"""Tests that never touch the network — they must stay free to run.

Anything requiring a real API call belongs in a separate, explicitly-marked
suite. Keeping the fast suite free means you'll actually run it.
"""

from __future__ import annotations

import pytest

from aicore.cost import Ledger, SpendLimitExceeded, cost_usd, price_for
from aicore.llm import _build_params


class FakeUsage:
    def __init__(self, inp: int, out: int, c_read: int = 0, c_write: int = 0) -> None:
        self.input_tokens = inp
        self.output_tokens = out
        self.cache_read_input_tokens = c_read
        self.cache_creation_input_tokens = c_write


def test_cost_matches_published_rates() -> None:
    # Opus 5 is $5/1M in, $25/1M out.
    assert cost_usd("claude-opus-5", 1_000_000, 0) == pytest.approx(5.00)
    assert cost_usd("claude-opus-5", 0, 1_000_000) == pytest.approx(25.00)
    assert cost_usd("claude-sonnet-5", 1_000_000, 1_000_000) == pytest.approx(12.00)


def test_cache_reads_are_cheaper_than_fresh_input() -> None:
    fresh = cost_usd("claude-opus-5", 100_000, 0)
    cached = cost_usd("claude-opus-5", 0, 0, cache_read_tokens=100_000)
    assert cached == pytest.approx(fresh * 0.1)


def test_unknown_model_does_not_understate_cost() -> None:
    """An unpriced model must assume the top tier, so estimates are never low."""
    unknown = price_for("claude-something-unreleased")
    assert unknown.input >= max(price_for(m).input for m in ("claude-opus-5", "claude-sonnet-5"))


def test_ledger_accumulates_and_enforces_limit(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("aicore.cost.REPO_ROOT", tmp_path)
    monkeypatch.setattr("aicore.cost.settings.spend_limit_usd", 0.05)

    led = Ledger()
    led.check_limit()  # under the limit: fine

    led.record("claude-opus-5", FakeUsage(1_000_000, 0), label="t")  # $5.00
    assert led.calls == 1
    assert led.total_usd == pytest.approx(5.00)

    with pytest.raises(SpendLimitExceeded):
        led.check_limit()


def test_ledger_writes_an_audit_line(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("aicore.cost.REPO_ROOT", tmp_path)
    led = Ledger()
    led.record("claude-opus-5", FakeUsage(10, 20), label="unit")
    lines = led.log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    assert '"label": "unit"' in lines[0]


def _params(model: str, **kw):
    defaults = dict(
        model=model,
        max_tokens=1000,
        effort="high",
        show_thinking=False,
        system=None,
        messages=[{"role": "user", "content": "hi"}],
        tools=None,
        cache_system=False,
        extra={},
    )
    defaults.update(kw)
    return _build_params(**defaults)


def test_opus5_gets_adaptive_thinking_and_fallbacks() -> None:
    params, needs_beta = _params("claude-opus-5")
    assert params["thinking"]["type"] == "adaptive"
    assert params["fallbacks"] == "default"
    assert needs_beta is True


def test_haiku_gets_no_thinking_param() -> None:
    """Haiku 4.5 needs the deprecated budget_tokens shape; sending adaptive 400s."""
    params, needs_beta = _params("claude-haiku-4-5")
    assert "thinking" not in params
    assert "fallbacks" not in params
    assert needs_beta is False


def test_sonnet5_thinks_but_has_no_fallbacks() -> None:
    params, needs_beta = _params("claude-sonnet-5")
    assert params["thinking"]["type"] == "adaptive"
    assert needs_beta is False


def test_effort_is_nested_in_output_config() -> None:
    """effort is not a top-level parameter — nesting it wrong is a silent 400."""
    params, _ = _params("claude-opus-5", effort="low")
    assert params["output_config"] == {"effort": "low"}
    assert "effort" not in params


def test_cache_system_marks_the_prefix_cacheable() -> None:
    params, _ = _params("claude-opus-5", system="stable prefix", cache_system=True)
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_show_thinking_toggles_display() -> None:
    off, _ = _params("claude-opus-5", show_thinking=False)
    on, _ = _params("claude-opus-5", show_thinking=True)
    assert off["thinking"]["display"] == "omitted"
    assert on["thinking"]["display"] == "summarized"
