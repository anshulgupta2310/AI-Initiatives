# Phase 1 — Retrieval (Weeks 3–6)

RAG is the single most common AI-engineer system-design prompt. The bar is not
"I used a vector DB" — it is chunking, hybrid retrieval, reranking, citations,
and a measurable evaluation.

Pick a corpus **you actually care about** and that has real structure: your
company's docs, a codebase, a set of papers, legal filings. Avoid toy datasets;
interviewers can tell, and messy data is where the learning is.

## Build order

Do these in sequence. Each stage must be measurably better than the last — and
you need Phase 3's eval harness to know. Build a crude version of the eval
(stage 1.5) before you start tuning.

### 1.1 — Brute force, no vector DB

Embed chunks with Voyage, store vectors in a numpy array, and do cosine
similarity by hand.

**Done when:** it answers questions over your corpus. **Do not install a vector
database yet.** You should feel the problem a vector DB solves before adopting
one — "why not just use numpy?" is a fair interview question and you want a real
answer about index structures and recall/latency tradeoffs at scale.

### 1.2 — Chunking that respects structure

Replace fixed-size chunking with structure-aware chunking (headings, function
boundaries, clause boundaries — whatever your corpus has).

Measure retrieval quality for: fixed 512, fixed 512 with 64 overlap,
structure-aware, and structure-aware with a parent-document fallback.

**Done when:** you have numbers, not opinions, and can explain why naive
fixed-size chunking splits the answer away from its context.

### 1.5 — A real eval, before you tune further

Build 40–60 question/answer pairs over your corpus by hand. Yes, by hand; this
is the part everyone skips and it is the part interviews probe hardest.

Measure **retrieval** and **generation** separately:

- Retrieval: recall@k, MRR, and nDCG. If the right chunk never arrives,
  no amount of prompt work saves you.
- Generation: faithfulness (is every claim supported by a retrieved chunk?) and
  answer correctness.

**Done when:** `uv run python 03-evals/run.py --suite rag` prints a scorecard,
and you have at least one case where retrieval succeeds but generation fails —
understanding that split is the whole point.

### 1.3 — Hybrid retrieval

Add BM25 keyword search alongside the dense vectors and fuse the rankings
(Reciprocal Rank Fusion is the standard starting point).

**Done when:** you can show a query where dense retrieval alone fails and hybrid
fixes it. Exact identifiers — error codes, function names, part numbers — are
where dense embeddings fall down. Have that example ready; it is a great
interview answer.

### 1.4 — Reranking

Add a cross-encoder reranker over the top ~50 candidates, returning the top ~8.

**Done when:** you can quantify the recall gain and state the latency cost. Then
answer: at what corpus size and QPS does this stop being worth it?

### 1.6 — Citations that are actually checkable

Every claim in the answer must carry a span-level citation that a user can click
to see the source text.

**Done when:** you have a script that samples answers and flags any uncited
claim. Then answer honestly: what is your hallucination rate now, measured?

### 1.7 — Now adopt a vector DB

Install the extra and migrate: `uv sync --extra vectordb`

**Done when:** you can explain what you gained over numpy (approximate indexes,
metadata filtering, persistence, concurrent writes) and what you gave up
(exact recall, operational simplicity).

## Interview questions this phase answers

- Design a RAG system over 10M documents. (Whiteboard it. Expect chunking,
  retrieval strategy, reranking, citations, and evals to all be probed.)
- Your users say the answers are confidently wrong. Debug it.
- Dense or keyword search? Why not both?
- How do you know your retrieval is any good?
- Why is your p99 latency 4 seconds, and how do you get it to 800ms?
