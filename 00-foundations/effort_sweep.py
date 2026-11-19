"""Exercise 0.3 — model x effort sweep on a single checkable task.

    uv run python 00-foundations/effort_sweep.py

45 calls (3 models x 3 efforts x 5 samples). Bump AI_SPEND_LIMIT_USD in .env
if you want the full grid guaranteed to finish — the ledger will stop the run
safely (no overspend) if it's hit partway through, and this script still
prints whatever it collected before stopping.
"""

from __future__ import annotations

import time
from itertools import product

from aicore.cost import SpendLimitExceeded
from aicore.llm import complete

PROBLEM = (
    "In 6 years, Maria will be three times as old as Ravi was 2 years ago. "
    "Maria is currently 24 years old. How old is Ravi now? "
    "End your answer with just the final number, nothing after it."
)
CORRECT_ANSWER = "12"

MODELS = ["claude-haiku-4-5", "claude-sonnet-5", "claude-opus-5"]
EFFORTS = ["low", "medium", "high"]
SAMPLES = 5

# Minimum accuracy to count as "clears the quality bar" when picking the
# cheapest usable cell. Naive on purpose — see 03-evals/README.md for why
# exact-match grading has real limits.
ACCURACY_BAR = 0.8


def is_correct(response_text: str) -> bool:
    """Naive exact-suffix match. Fine for a first pass; Phase 3 is where
    you'll build graders that don't break on formatting variance."""
    cleaned = response_text.strip().rstrip(".*_ \n")
    return cleaned.endswith(CORRECT_ANSWER)


def run_sweep() -> list[dict]:
    results: list[dict] = []
    try:
        for model, effort in product(MODELS, EFFORTS):
            correct_count = 0
            total_cost = 0.0
            total_latency = 0.0

            for _ in range(SAMPLES):
                start = time.time()
                result = complete(
                    PROBLEM,
                    model=model,
                    effort=effort,
                    label=f"sweep:{model}:{effort}",
                )
                total_latency += time.time() - start
                total_cost += result.cost_usd
                if is_correct(result.text):
                    correct_count += 1

            row = {
                "model": model,
                "effort": effort,
                "accuracy": correct_count / SAMPLES,
                "avg_cost": total_cost / SAMPLES,
                "avg_latency": total_latency / SAMPLES,
            }
            results.append(row)
            print(
                f"{model:20} {effort:8} accuracy={correct_count}/{SAMPLES} "
                f"avg_cost=${row['avg_cost']:.5f} avg_latency={row['avg_latency']:.2f}s"
            )
    except SpendLimitExceeded as e:
        print(f"\nStopped early — spend limit reached: {e}")

    return results


def print_table(results: list[dict]) -> None:
    print("\n| Model | Effort | Accuracy | Avg Cost | Avg Latency |")
    print("|---|---|---|---|---|")
    for r in results:
        print(
            f"| {r['model']} | {r['effort']} | {r['accuracy']:.0%} "
            f"| ${r['avg_cost']:.5f} | {r['avg_latency']:.2f}s |"
        )

    passing = [r for r in results if r["accuracy"] >= ACCURACY_BAR]
    passing.sort(key=lambda r: r["avg_cost"])
    if passing:
        best = passing[0]
        print(
            f"\nCheapest cell clearing {ACCURACY_BAR:.0%} accuracy: "
            f"{best['model']} @ {best['effort']} (${best['avg_cost']:.5f}/call)"
        )
    else:
        print(f"\nNo cell cleared {ACCURACY_BAR:.0%} accuracy.")


if __name__ == "__main__":
    results = run_sweep()
    print_table(results)
