"""Proves the toolchain works end to end. Run this first.

    uv run python 00-foundations/smoke_test.py

Costs roughly $0.01. Every number it prints is one you should be able to
explain in an interview.
"""

from __future__ import annotations

import sys

from rich.console import Console

from aicore import complete, count_tokens, ledger, settings, stream_text

console = Console()

LONG_CONTEXT = "You are reviewing an internal engineering handbook.\n\n" + "\n".join(
    f"Section {i}: Service {i} owns the {['billing', 'auth', 'search', 'notify'][i % 4]} "
    f"domain. Its on-call rotation is team-{i % 7}. Its p99 latency budget is {50 + i * 3}ms."
    for i in range(200)
)


def section(n: int, title: str) -> None:
    console.print(f"\n[bold cyan]{n}. {title}[/bold cyan]")


def main() -> int:
    console.print(f"[dim]model={settings.model}  effort={settings.effort}[/dim]")

    # 1 — Does the key work at all?
    section(1, "Basic request")
    r = complete(
        "In one sentence, what is the difference between a vector index and a database index?",
        label="smoke:basic",
    )
    if r.refused:
        console.print(f"[red]Declined (category={r.refusal_category})[/red]")
        return 1
    console.print(r.text.strip())
    console.print(f"[dim]{r.input_tokens} in / {r.output_tokens} out = ${r.cost_usd:.5f}[/dim]")

    # 2 — Count before you send. This is how you predict a bill.
    section(2, "Token counting")
    n = count_tokens(LONG_CONTEXT)
    console.print(f"The handbook context is [bold]{n:,}[/bold] input tokens.")
    console.print("[dim]Server-side count. tiktoken would give a wrong number here.[/dim]")

    # 3 — Prompt caching. Same stable prefix twice; watch the second call.
    section(3, "Prompt caching")
    q = "Which team is on call for Service 42?"
    first = complete(q, system=LONG_CONTEXT, cache_system=True, label="smoke:cache-write")
    second = complete(q, system=LONG_CONTEXT, cache_system=True, label="smoke:cache-read")
    console.print(f"call 1: cache_read={first.cache_read_tokens:,} tokens")
    console.print(f"call 2: cache_read={second.cache_read_tokens:,} tokens")
    if second.cache_read_tokens > 0:
        saved = 1 - (second.cost_usd / first.cost_usd) if first.cost_usd else 0
        console.print(f"[green]Cache hit — call 2 cost {saved:.0%} less.[/green]")
    else:
        console.print(
            "[yellow]No cache hit. Either the prefix is under the model's minimum "
            "cacheable size, or something in it varied between calls.[/yellow]"
        )

    # 4 — Streaming, which is what you use for anything user-facing.
    section(4, "Streaming")
    for chunk in stream_text(
        "Name the three things an LLM eval must measure. One line each, no preamble.",
        max_tokens=2_000,
        label="smoke:stream",
    ):
        print(chunk, end="", flush=True)
    print()

    console.print(f"\n[bold green]All checks passed.[/bold green] {ledger.summary()}")
    console.print(f"[dim]Per-call audit trail: {ledger.log_path}[/dim]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
