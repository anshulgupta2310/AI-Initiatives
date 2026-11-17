# Phase 0 — Foundations (Weeks 1–2)

The goal is to stop treating the model as magic. By the end you should be able to
predict roughly what a request will cost and why it behaved the way it did.

Run the smoke test first:

```bash
uv run python 00-foundations/smoke_test.py
```

Read `src/aicore/llm.py` line by line before starting. You will extend it all
course; you should understand every branch in it.

## Exercises

### 0.1 — Structured output you can trust

Write `extract.py` that takes a messy block of text (invoice, resume, support
email — your choice) and returns a validated Pydantic model.

- Use `output_config={"format": ...}` (structured outputs), **not** "respond in
  JSON" in the prompt, and not a regex on the response.
- Feed it three deliberately broken inputs: missing fields, contradictory
  fields, and an input that is not an invoice at all.

**Done when:** malformed input produces a typed validation failure you handle,
never a crash and never a silently wrong object. Write down what the model does
when you ask for a field that genuinely is not in the document — the honest
answer is the interesting one.

### 0.2 — Make caching work, then break it

Write `cache_lab.py` with a ~20k-token stable prefix and 10 varying questions.

- Measure total cost with caching on versus off.
- Then deliberately break the cache four ways: put a timestamp in the system
  prompt, reorder the tool list, use unsorted `json.dumps`, and change one byte
  at the start of the prefix.

**Done when:** you can state the cache invalidation rule from memory and have a
table of the measured cost of each mistake.

> Why this matters: "our prompt cache hit rate is 4%, find out why" is a real
> on-the-job task and a common interview probe. Having measured it is the
> difference between an answer and a guess.

### 0.3 — Effort and model sweep

Take one genuinely hard task (a multi-step reasoning problem with a checkable
answer). Run it across `{haiku-4-5, sonnet-5, opus-5}` × `{low, medium, high}`
effort, 5 samples each.

**Done when:** you have a table of accuracy, latency, and cost per cell, and you
can name the cheapest cell that still clears your quality bar. This table is a
portfolio artifact — keep it.

### 0.4 — The tool-use loop, by hand

Write `manual_loop.py`: a `while response.stop_reason == "tool_use"` loop with
two tools, no framework and no SDK tool-runner helper.

- Handle a tool that raises (return `tool_result` with `is_error: True` — do not
  drop the block).
- Handle parallel tool calls: when one assistant message contains two
  `tool_use` blocks, return **both** results in a single user message.

**Done when:** you can draw the loop on a whiteboard from memory. This gets asked
directly, and most candidates who only ever used a framework cannot do it.

## Interview questions this phase answers

- Walk me through what happens between `messages.create` and the response.
- Why is my cache hit rate zero?
- How do you guarantee the model returns valid JSON?
- Our inference bill tripled. Where do you look first?
- Implement an agent loop. No frameworks.
