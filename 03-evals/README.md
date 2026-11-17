# Phase 3 — Evals (Weeks 10–12)

**This is the phase that gets you hired.** Evals are the most heavily weighted
and most commonly failed area in current AI-engineer interviews. Nearly every
candidate can wire up a RAG demo; very few can tell you whether it works, or
prove a change made it better.

If you are short on time, cut Phase 4 before you cut this.

You will have written a crude eval in Phase 1.5. Here you make it trustworthy.

## Build order

### 3.1 — A real harness

Build `run.py` so that `uv run python 03-evals/run.py --suite rag` runs a
versioned suite and writes results to disk.

Requirements:

- Deterministic case IDs; results diffable between runs.
- A **train/validation/test split.** Tune on train, sanity-check on validation,
  and report the test number. Tuning against your test set is how you fool
  yourself.
- Per-case cost and latency, not just correctness.
- Results stored per run so you can plot a trajectory over time.

### 3.2 — Graders, in increasing order of cost

Implement and know when to use each:

| Grader | Use when |
|---|---|
| Exact / fuzzy match | There is one right answer |
| Programmatic assertion | Structure or a property is checkable in code |
| LLM-as-judge, rubric | Quality is subjective but describable |
| Human review | Calibrating everything above |

**The critical step everyone skips:** validate your LLM judge against human
labels. Hand-label 50 cases yourself, then measure judge/human agreement
(Cohen's kappa). **A judge you have not calibrated is not a measurement.**

**Done when:** you can state your judge's agreement rate with you. If it's
below ~0.6, fix the rubric before trusting a single number it produces.

### 3.3 — Agent evals, which are different

Final-answer scoring is not enough for agents. Implement all three:

- **Trajectory** — were the steps reasonable? Did it take 3 tool calls or 40?
- **Tool-call correctness** — right tool, right arguments.
- **Final answer** — rubric-based judge on the output.

**Done when:** you can show an agent run that produced the right answer through
a terrible path, and explain why that still matters (cost, latency, fragility).

### 3.4 — Regression gating

Wire the eval into CI (GitHub Actions). A PR that drops the test score fails.

**Done when:** you have a PR in your own repo that CI blocked for a quality
regression. Screenshot it. That is a genuinely strong portfolio artifact — very
few candidates have one.

### 3.5 — Hill-climb something, honestly

Pick your worst metric and improve it over 5+ measured iterations. Keep a log:
hypothesis, change, train score, test score.

**Done when:** you have a trajectory showing real improvement, *and* at least
one iteration where your change made things worse and you reverted it. Say that
out loud in interviews — it signals you measure rather than vibe.

## Interview questions this phase answers

- How do you know your LLM feature works?
- How do you evaluate something with no single right answer?
- Your eval says 94% but users complain. What's wrong with your eval?
- How do you keep an LLM-as-judge honest?
- How do you evaluate an agent, not just an answer?
- How do you stop a prompt change from silently regressing quality?
