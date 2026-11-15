# Metric Anomaly Investigator

A self-improving AI agent (built with [Agno](https://github.com/agno-agi/agno)) that investigates
anomalies in **real** daily download numbers from crates.io (the Rust package registry).
No fake data: every number comes from the live crates.io API.

> "Downloads of `rand` jumped 32% on Oct 10. Why?" -> the agent decides what to check, runs
> queries, and reports a cause with evidence. Humans grade it, and it learns.

## 1. Feasibility check (tested from this environment, 2026-11-15)

| Source | Result | Use |
|---|---|---|
| crates.io API `/crates/{c}/downloads` | OK, 90 days daily downloads, split by version | **The metric** |
| crates.io API `/crates/{c}` | OK, every version with release time + yank flag | **The candidate causes** |
| PyPI / npm registry metadata | OK | Release dates only, no download counts |
| pypistats, npm downloads API, Wikimedia, GH Archive | Blocked in this sandbox | Not used |
| BigQuery public PyPI dataset | Reachable, but needs GCP credentials | Not used |
| GitHub REST API (releases) | 403 outside the session's repo | Not used |
| crates.io full DB dump | Blocked in this sandbox | Not used |

Data quality (12 crates, 5,627 rows, 2026-08-18 to 2026-11-15):
- 90 complete days per crate, 6 rows/day (top 5 versions + an "other versions" bucket).
- **Today (UTC) is partial** (about half of a normal day) so it is excluded from all analysis.
- Weekly seasonality is strong (weekends about 30% lower) so deviations use a same-weekday baseline.
- crates.io only serves the last 90 days. `ingest.py --loop` accumulates history beyond that.

## 2. Assumptions

1. Metric = total daily downloads per crate (sum of version rows + "other" bucket).
2. Baseline = median of the same weekday over the previous 4 weeks (needs >= 3 points).
3. Anomaly = |deviation| >= 15% (configurable). The data has no drops worse than about -10% in this window, so the agent investigates both drops **and surges**.
4. Downloads include CI and bot traffic. Organic usage can't be separated, which is one of the causes the agent tests for.
5. The 12-crate watchlist is a sample. It is enough to test "ecosystem-wide vs crate-specific".
6. Ground truth comes from a human grading the agent (`feedback.py`), not from an automatic oracle.
7. crates.io etiquette: <= 1 request/sec, identifying User-Agent.

## 3. How it works

```
ingest.py -> data/crates.db (SQLite) -> tools.py (10 tools) -> agent.py (Agno + any LLM, see llm.py)
                                              ^                         |
                                  feedback.py (human grades) <- record_investigation
```

**Why it is an agent:** it picks its own next tool call from what it finds (scan, peers, version
breakdown, releases, ad-hoc SQL), and it stops when the evidence is decisive. There is a hard cap of 25 tool calls.

**How it self-improves:**
1. After each run it logs a structured conclusion (`investigations` table).
2. You grade it: `python feedback.py confirm 3` or `python feedback.py correct 3 ECOSYSTEM_WIDE "why"`.
3. Grades become lessons. The agent calls `recall_memory` first on every run and reads them, along with its
   graded track record by cause.
4. Success looks like fewer tool calls and fewer corrected conclusions over time.

Guardrails: tools are read-only (`run_sql` allows a single SELECT on a read-only connection), the
agent can only write to its own memory tables, and the cause list is fixed.

## 4. Run it

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python ingest.py --export          # fetch real data (~30s); --loop 6 for continuous ingestion
python smoke_test.py               # tests every tool on real data, no API key needed
export OPENROUTER_API_KEY=...     # or XAI_API_KEY / GROQ_API_KEY / ANTHROPIC_API_KEY
# optional: LLM_PROVIDER=openrouter|xai|groq|anthropic   LLM_MODEL=<model id>
python agent.py                    # agent picks the biggest recent anomaly
python agent.py "Why did rand jump on 2026-10-10?"
python feedback.py list            # then confirm / correct
```

CSV snapshots of the ingested data are in `data/snapshots/`.

## 5. Status

- Ingestion, tools, memory and the Agno agent are built, and every tool passes against real data.
- **The live LLM loop has not been run yet.** The build environment had no model API key.
  Run `python agent.py` with your key (OpenRouter, xAI Grok, Groq, or Anthropic) to see the first investigation.
- No investigations have been graded yet, so no lessons exist and no improvement has been observed.
