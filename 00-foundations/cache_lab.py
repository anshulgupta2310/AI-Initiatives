from pathlib import Path

from aicore.llm import complete

DESIGN_PATTERN_DOC = Path("00-foundations/design_patterns.md").read_text()

QUESTIONS = [
    "Which pattern would you use for implementing undo/redo in a text editor?",
    "What's the key difference between Strategy and State?",
    "I need to support three different notification channels without subclassing per channel. Which pattern fits?",
    # "Why does Spring's @Transactional rely on the Proxy pattern specifically?",
    # "When would Composite be a worse fit than a flat list with type checks?",
    # "Name a pattern that's built into Java's own for-each loop syntax.",
    # "What goes wrong if a Memento's Caretaker is allowed to read the snapshot's internal fields?",
    # "Give an example of where Abstract Factory beats a single Factory Method.",
    # "Why is the Singleton pattern considered risky for unit testing?",
    # "What's the practical difference between Adapter and Facade?",
]


def run_trial(cache: bool) -> float:
    total_cost = 0.0
    for question in QUESTIONS:
        result = complete(
            question,
            system=DESIGN_PATTERN_DOC,
            cache_system=cache,
            effort="low",
            label=f"cache_lab:{'cached' if cache else 'uncached'}",
        )
        total_cost += result.cost_usd
        print(
            f"cache_read={result.cache_read_tokens:>6} cost=${result.cost_usd:.5f}  {question[:50]}..."
            f"response: {result.text[:50]}..."
        )
    return total_cost


if __name__ == "__main__":
    # print("Without caching:")
    # uncached_total = run_trial(cache=False)

    print("\nWith caching:")
    cached_total = run_trial(cache=True)

    # print(f"\nUncached total: ${uncached_total:.4f}")
    print(f"Cached total:   ${cached_total:.4f}")
    # if uncached_total:
    #     print(f"Savings: {1 - (cached_total / uncached_total):.0%}")
