"""Token accounting.

Cost awareness is a real interview topic — "how would you bring this feature's
bill down?" is asked constantly. Measuring it from day one beats guessing.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from aicore.config import REPO_ROOT, settings


class SpendLimitExceeded(RuntimeError):
    """Raised before a request that would push this process past the limit."""


@dataclass(frozen=True)
class Price:
    """USD per 1M tokens."""

    input: float
    output: float

    # Cache reads bill at ~0.1x input; cache writes at ~1.25x input.
    @property
    def cache_read(self) -> float:
        return self.input * 0.1

    @property
    def cache_write(self) -> float:
        return self.input * 1.25


# Source: Anthropic pricing, verified 2026-11-17. Check the console before
# quoting these in an interview — they move.
PRICING: dict[str, Price] = {
    "claude-fable-5-1": Price(input=10.00, output=50.00),
    "claude-opus-5": Price(input=5.00, output=25.00),
    "claude-opus-4-8": Price(input=5.00, output=25.00),
    "claude-sonnet-5": Price(input=2.00, output=10.00),
    "claude-haiku-4-5": Price(input=1.00, output=5.00),
}


def price_for(model: str) -> Price:
    if model in PRICING:
        return PRICING[model]
    # Unknown model: assume the most expensive tier so estimates never
    # understate the bill.
    return Price(input=10.00, output=50.00)


def cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    p = price_for(model)
    return (
        input_tokens * p.input
        + output_tokens * p.output
        + cache_read_tokens * p.cache_read
        + cache_write_tokens * p.cache_write
    ) / 1_000_000


@dataclass
class Ledger:
    """Process-wide running total, with an on-disk audit trail."""

    total_usd: float = 0.0
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def log_path(self) -> Path:
        return REPO_ROOT / ".cost_log.jsonl"

    def check_limit(self) -> None:
        if self.total_usd >= settings.spend_limit_usd:
            raise SpendLimitExceeded(
                f"This process has spent ${self.total_usd:.4f}, at or over the "
                f"${settings.spend_limit_usd:.2f} limit. Raise AI_SPEND_LIMIT_USD "
                f"in .env if that is intended."
            )

    def record(self, model: str, usage: object, label: str = "") -> float:
        """Add one call's usage to the running total. Returns its cost in USD."""
        inp = int(getattr(usage, "input_tokens", 0) or 0)
        out = int(getattr(usage, "output_tokens", 0) or 0)
        c_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        c_write = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)

        spend = cost_usd(model, inp, out, c_read, c_write)

        with self._lock:
            self.total_usd += spend
            self.calls += 1
            self.input_tokens += inp
            self.output_tokens += out
            self.cache_read_tokens += c_read

        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "label": label,
            "model": model,
            "input_tokens": inp,
            "output_tokens": out,
            "cache_read_input_tokens": c_read,
            "cache_creation_input_tokens": c_write,
            "cost_usd": round(spend, 6),
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        return spend

    def summary(self) -> str:
        cached = ""
        if self.cache_read_tokens:
            pct = 100 * self.cache_read_tokens / max(1, self.input_tokens + self.cache_read_tokens)
            cached = f", {pct:.0f}% of input served from cache"
        return (
            f"{self.calls} call(s), {self.input_tokens:,} in / "
            f"{self.output_tokens:,} out, ${self.total_usd:.4f}{cached}"
        )


ledger = Ledger()
