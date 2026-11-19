"""One place where this repo talks to Claude.

Everything downstream (RAG, agents, evals, the API) goes through `complete` or
`stream_text`, so cost accounting, refusal handling, and error handling are
written once instead of re-improvised per script.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

import anthropic

from aicore.config import Effort, settings
from aicore.cost import ledger

# Models that take adaptive thinking. Haiku 4.5 and older still use the
# deprecated budget_tokens shape, so this wrapper simply leaves thinking off
# for them rather than carrying two code paths.
_ADAPTIVE_THINKING_MODELS = (
    "claude-fable-5",
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-sonnet-5",
)

# Server-side refusal fallbacks: if a safety classifier declines the request,
# the API re-runs it on a fallback model inside the same call instead of
# handing you an empty response. Only the newest models support it.
_FALLBACK_MODELS = ("claude-fable-5", "claude-opus-5")
_FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Models that take output_config.effort. Haiku 4.5 predates this parameter
# and returns a 400 if it's present at all — not just an unsupported value.
_EFFORT_MODELS = (
    "claude-fable-5",
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-sonnet-5",
)


@lru_cache(maxsize=1)
def client() -> anthropic.Anthropic:
    settings.require_anthropic_key()
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


@dataclass
class LLMResult:
    """What came back, plus what it cost."""

    text: str
    content: list[Any]
    stop_reason: str | None
    model: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    thinking: str = ""
    request_id: str | None = None
    refusal_category: str | None = None

    @property
    def refused(self) -> bool:
        return self.stop_reason == "refusal"

    @property
    def truncated(self) -> bool:
        """True when max_tokens cut the response off mid-thought."""
        return self.stop_reason == "max_tokens"


def _supports(model: str, prefixes: tuple[str, ...]) -> bool:
    return any(model.startswith(p) for p in prefixes)


def _build_params(
    *,
    model: str,
    max_tokens: int,
    effort: Effort,
    show_thinking: bool,
    system: str | list[dict[str, Any]] | None,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    cache_system: bool,
    extra: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Assemble request kwargs. Returns (params, needs_beta_namespace)."""
    params: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }

    if _supports(model, _EFFORT_MODELS):
        params["output_config"] = {"effort": effort}

    if _supports(model, _ADAPTIVE_THINKING_MODELS):
        # display defaults to "omitted" on current models, which streams empty
        # thinking blocks. Ask for a summary only when the caller wants to see it.
        params["thinking"] = {
            "type": "adaptive",
            "display": "summarized" if show_thinking else "omitted",
        }

    if system is not None:
        if cache_system and isinstance(system, str):
            # Stable prefix -> cacheable. Keep volatile content out of `system`.
            params["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]
        else:
            params["system"] = system

    if tools:
        params["tools"] = tools

    needs_beta = False
    if _supports(model, _FALLBACK_MODELS):
        params["betas"] = [_FALLBACK_BETA]
        params["fallbacks"] = "default"
        needs_beta = True

    params.update(extra)
    return params, needs_beta


def _extract(response: Any, model: str, label: str) -> LLMResult:
    text_parts: list[str] = []
    thinking_parts: list[str] = []

    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "thinking":
            thinking_parts.append(getattr(block, "thinking", "") or "")

    spend = ledger.record(model, response.usage, label=label)

    category = None
    if response.stop_reason == "refusal" and getattr(response, "stop_details", None):
        category = getattr(response.stop_details, "category", None)

    usage = response.usage
    return LLMResult(
        text="".join(text_parts),
        content=list(response.content),
        stop_reason=response.stop_reason,
        model=getattr(response, "model", model),
        cost_usd=spend,
        input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
        output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        cache_read_tokens=int(getattr(usage, "cache_read_input_tokens", 0) or 0),
        thinking="".join(thinking_parts),
        request_id=getattr(response, "_request_id", None),
        refusal_category=category,
    )


def complete(
    prompt: str | list[dict[str, Any]] | None = None,
    *,
    system: str | list[dict[str, Any]] | None = None,
    messages: list[dict[str, Any]] | None = None,
    model: str | None = None,
    effort: Effort | None = None,
    max_tokens: int = 16_000,
    tools: list[dict[str, Any]] | None = None,
    show_thinking: bool = False,
    cache_system: bool = False,
    label: str = "",
    **extra: Any,
) -> LLMResult:
    """Single non-streaming request.

    Pass either `prompt` (a string, for one-shot calls) or `messages` (the full
    history, for multi-turn and tool loops) — not both.

    `max_tokens` defaults to 16k, which keeps a non-streaming request inside the
    SDK's HTTP timeout. For anything longer, use `stream_text`.
    """
    if (prompt is None) == (messages is None):
        raise ValueError("Pass exactly one of `prompt` or `messages`.")

    model = model or settings.model
    effort = effort or settings.effort
    msgs = messages if messages is not None else [{"role": "user", "content": prompt}]

    ledger.check_limit()

    params, needs_beta = _build_params(
        model=model,
        max_tokens=max_tokens,
        effort=effort,
        show_thinking=show_thinking,
        system=system,
        messages=msgs,
        tools=tools,
        cache_system=cache_system,
        extra=extra,
    )

    c = client()
    try:
        target = c.beta.messages if needs_beta else c.messages
        response = target.create(**params)
    # Most specific first — collapsing these into one `except` throws away the
    # retryable/non-retryable distinction, which is a common review comment.
    except anthropic.AuthenticationError as e:
        raise RuntimeError("ANTHROPIC_API_KEY was rejected. Check the key in .env.") from e
    except anthropic.NotFoundError as e:
        raise RuntimeError(f"Model {model!r} not found. Check AI_MODEL in .env.") from e
    except anthropic.BadRequestError as e:
        raise RuntimeError(f"Malformed request: {e.message}") from e
    except anthropic.RateLimitError as e:
        retry_after = e.response.headers.get("retry-after", "60")
        raise RuntimeError(f"Rate limited; retry after {retry_after}s.") from e
    except anthropic.APIConnectionError as e:
        raise RuntimeError("Could not reach the API. Check your network.") from e

    return _extract(response, model, label or "complete")


def stream_text(
    prompt: str | None = None,
    *,
    system: str | None = None,
    messages: list[dict[str, Any]] | None = None,
    model: str | None = None,
    effort: Effort | None = None,
    max_tokens: int = 64_000,
    show_thinking: bool = False,
    cache_system: bool = False,
    label: str = "",
    **extra: Any,
) -> Iterator[str]:
    """Stream text deltas. Cost is recorded once the stream completes.

    Streaming is the right default for long outputs — it avoids the HTTP
    timeout you hit with a large non-streaming `max_tokens`.
    """
    if (prompt is None) == (messages is None):
        raise ValueError("Pass exactly one of `prompt` or `messages`.")

    model = model or settings.model
    effort = effort or settings.effort
    msgs = messages if messages is not None else [{"role": "user", "content": prompt}]

    ledger.check_limit()

    params, needs_beta = _build_params(
        model=model,
        max_tokens=max_tokens,
        effort=effort,
        show_thinking=show_thinking,
        system=system,
        messages=msgs,
        tools=None,
        cache_system=cache_system,
        extra=extra,
    )

    c = client()
    target = c.beta.messages if needs_beta else c.messages
    with target.stream(**params) as stream:
        yield from stream.text_stream
        final = stream.get_final_message()

    ledger.record(model, final.usage, label=label or "stream")

    if final.stop_reason == "refusal":
        category = getattr(getattr(final, "stop_details", None), "category", None)
        raise RuntimeError(f"Request was declined (category: {category}).")


def count_tokens(
    prompt: str | None = None,
    *,
    system: str | None = None,
    messages: list[dict[str, Any]] | None = None,
    model: str | None = None,
) -> int:
    """Exact input-token count, server-side. Never estimate with tiktoken —
    it is a different tokenizer and the number will be wrong."""
    model = model or settings.model
    msgs = messages if messages is not None else [{"role": "user", "content": prompt or ""}]
    kwargs: dict[str, Any] = {"model": model, "messages": msgs}
    if system:
        kwargs["system"] = system
    return int(client().messages.count_tokens(**kwargs).input_tokens)


Role = Literal["user", "assistant"]
