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

## 3. The dashboard (for product managers)

```bash
streamlit run app.py
```

| Page | What a PM does there |
|---|---|
| **Overview** | Monitor health, accuracy as you grade, tool calls per run, tokens, failures |
| **Run the agent** | Let it choose, pick an anomaly, or ask your own question. See every tool call it made |
| **Review & grade** | Confirm or correct its conclusions. This is the learning signal |
| **Memory** | Choose how memory is used (agent looks it up / always in prompt / off), add your own lessons, delete bad ones, backup and restore |
| **Configure** | Edit the system prompt (versioned, with diff and rollback), enable/disable tools and rewrite their descriptions, set thresholds and limits, edit the cause list, add saved SQL queries as tools, pick the model, edit the watchlist |
| **Data explorer** | Real download charts with releases marked, anomaly list, refresh from crates.io |

API keys are typed in the sidebar and kept in the browser session only (never written to disk).
Set `APP_PASSWORD` to require a password on a public deployment.

## 4. How it works

```
ingest.py -> crates.db -> tools.py (11 tools) -> runner.py (Agno agent) <- config.py (prompt, tools, memory, thresholds)
                                                      |
                              runs / investigations --+--> feedback (Review page) --> lessons --> next run
```

**Why it is an agent:** it picks its own next tool call from what it finds, and stops when the evidence is
decisive, with a hard cap on tool calls.

**How it self-improves:** it logs a structured conclusion, a human grades it, the grade becomes a lesson,
and the lesson is in memory on the next run. Success looks like higher accuracy and fewer tool calls over time.

Guardrails: tools are read-only (single SELECT on a read-only connection); the agent can only write to its own
memory tables; conclusions are limited to the cause list; the tool-call cap is enforced by the framework.

## 5. Run it

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
streamlit run app.py               # dashboard (seeds itself from data/snapshots/ on first start)
python smoke_test.py               # tests every tool on real data, no API key needed
python agent.py "Why did rand jump on 2026-10-10?"   # CLI, needs a model key
python ingest.py --loop 6          # keep pulling fresh data every 6 hours
```

## 6. Deploy

Streamlit needs a Python server, so it cannot run on GitHub Pages (static files only). `render.yaml` deploys
it to Render. **Free hosting resets the disk on restart**, so lessons and settings are lost unless you use the
Memory page's backup/restore, or move to a paid plan with a disk (see comments in `render.yaml`).

## 7. Status

- Ingestion, tools, memory, the Agno agent, and the dashboard are built. Every tool, every dashboard page,
  and the run -> grade -> lesson loop were tested headlessly against the real data.
- The agent loop was tested with a **scripted fake model** (to verify the plumbing), not a real LLM.
  Whether a real model investigates *well* is untested until you run it with your key.
- No real investigations have been graded yet, so no improvement has been observed.
