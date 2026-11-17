# Phase 4 — Production (Weeks 13–16)

Your SWE background is the advantage here — most AI-engineer candidates are weak
on exactly this, so it is where you can differentiate cheaply. Lean on it.

## Build order

### 4.1 — Serve it

Build a FastAPI service in `api/` exposing your RAG + agent work.

Requirements:

- **Token streaming to the browser** (SSE). A blocking 8-second POST is not a
  product.
- Request/response logging with trace IDs that correlate to your agent traces.
- Timeouts, retries with backoff, and a circuit breaker for upstream failures.
- Health and readiness endpoints that mean different things.
- Per-user rate limiting and a per-request cost ceiling.

**Done when:** `uv run uvicorn aicore.api:app --reload` serves the React app in
`web/` with tokens streaming in, and you can kill the upstream and watch it
degrade gracefully rather than hang.

### 4.2 — The frontend

Wire up `web/` (Vite + React + TS, already scaffolded) to stream from the API.

- Render tokens as they arrive.
- Show citations as clickable spans.
- Show cost and latency per message. Making cost visible in the UI is an
  unusual, memorable portfolio touch.
- Handle mid-stream errors without losing the partial response.

### 4.3 — Observability

Instrument with OpenTelemetry. Pick one backend (Langfuse and Arize Phoenix
both self-host free) and ship traces to it.

**Done when:** you can answer, from dashboards alone: what is my p99? my cost
per request? my cache hit rate? which prompt version is live? what fraction of
requests hit a tool error?

### 4.4 — Make it cheaper, with evidence

Take your p50 cost per request down by 50%+ without dropping your eval score.

Work the levers in order — free wins before quality tradeoffs:

1. Prompt caching (verify `cache_read_input_tokens` is non-zero)
2. Input-token hygiene — stop sending context that does not change the answer
3. Output-token hygiene — stop asking for prose you discard
4. Batch API for anything not latency-sensitive (50% off)
5. *Then* effort reduction, and only then a cheaper model

**Done when:** you have a before/after table of cost **and** eval score. Cost
reduction with no eval score next to it is not an accomplishment, and a good
interviewer will say so.

### 4.5 — Ship it where someone can use it

Dockerize, deploy somewhere with a public URL (Fly.io, Railway, Render), and put
the link in your README.

**Done when:** a stranger can use it without you present. A working link beats
a repo, every time.

## Interview questions this phase answers

- Design the serving architecture for an LLM feature at 1000 QPS.
- How do you stream tokens through your stack?
- Our p99 is 12 seconds. Walk me through diagnosing it.
- Cut this feature's cost in half without hurting quality.
- An upstream model provider has an outage. What do your users see?
- What do you monitor in an LLM app that you wouldn't in a normal service?
