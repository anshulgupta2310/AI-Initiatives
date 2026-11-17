# AI-Initiatives

Practical AI engineering, built in public: retrieval, agents, evaluation, and
production serving. Target role: **AI / LLM Application Engineer.**

Every phase is built to answer specific interview questions, listed at the
bottom of each phase README.

## Quick start

```bash
cp .env.example .env          # then paste your Anthropic API key
uv sync                       # Python deps into .venv
uv run python 00-foundations/smoke_test.py
```

```bash
uv run pytest                 # fast, no network, no cost
uv run ruff check . && uv run mypy src/
cd web && npm install && npm run dev
```

## Layout

| Path | What lives here |
|---|---|
| `src/aicore/` | Shared client, cost ledger, config. Everything goes through here. |
| `00-foundations/` | Raw API: caching, tokens, structured output, manual tool loop |
| `01-rag/` | Retrieval: chunking, hybrid search, reranking, citations |
| `02-agents/` | Agents: tools, budgets, context management, adversarial testing |
| `03-evals/` | Eval harness, graders, judge calibration, CI gating |
| `04-production/` | FastAPI serving, streaming, observability, cost work |
| `web/` | Vite + React + TS frontend |
| `tests/` | Fast offline tests |

## Ground rules

These are the habits that separate a portfolio from a pile of demos.

1. **Measure before optimizing.** Every claim of improvement needs a number
   next to it. "It feels better" is not a result.
2. **Evals before features.** If you can't measure it, you can't tell whether
   your next change helped. Phase 3 exists for a reason.
3. **Build it by hand once.** Implement the loop, the retrieval, the fusion
   yourself before adopting a framework. You cannot defend code you only
   configured.
4. **Keep cost visible.** `aicore.ledger` logs every call to `.cost_log.jsonl`
   with a hard spend ceiling from `AI_SPEND_LIMIT_USD`. Read it often.
5. **Commit the failures.** The reverted experiment and the eval that caught a
   regression are better interview material than the happy path.

## Cost control

The default model is `claude-opus-5` ($5/$25 per 1M tokens). While learning,
`claude-sonnet-5` ($2/$10) or `claude-haiku-4-5` ($1/$5) is usually plenty —
set `AI_MODEL` in `.env`. Lowering `AI_EFFORT` to `low` or `medium` cuts cost
further.

`AI_SPEND_LIMIT_USD` (default $2.00) is enforced per process before each
request, so a runaway agent loop fails loudly instead of billing you.

Check your spend any time:

```bash
uv run python -c "
import json,collections
from pathlib import Path
rows=[json.loads(l) for l in Path('.cost_log.jsonl').read_text().splitlines()]
by=collections.Counter()
for r in rows: by[r['label']] += r['cost_usd']
print(f'total \${sum(by.values()):.4f} over {len(rows)} calls')
for k,v in by.most_common(10): print(f'  {k:28} \${v:.4f}')
"
```

## Progress

Tick these off as you go; this doubles as the summary bullet list you'll pull
from when writing applications.

- [ ] Phase 0 — Foundations
- [ ] Phase 1 — Retrieval
- [ ] Phase 3 — Evals (start the harness during Phase 1)
- [ ] Phase 2 — Agents
- [ ] Phase 4 — Production
- [ ] Deployed with a public URL
- [ ] CI blocking quality regressions
