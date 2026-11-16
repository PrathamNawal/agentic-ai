# Complaint Anomaly Investigator

A self-improving AI agent (built with [Agno](https://github.com/agno-agi/agno)) that investigates
spikes and drops in **real** consumer-complaint volume, with a dashboard where a product manager can
monitor it, tune it, and teach it. No synthetic data.

> "Wells Fargo complaints jumped from ~44 a day to 1,213 on 2023-01-20. Why?" -> the agent decides what to
> check (peers, product, issue, channel, known events), reports a cause with evidence, and learns from
> your grade.

## 1. The data

| | |
|---|---|
| **Source** | Public [CFPB consumer-complaints database](https://www.consumerfinance.gov/data-research/consumer-complaints/), via the CC0 Hugging Face mirror [BEE-spoke-data/consumer-finance-complaints](https://huggingface.co/datasets/BEE-spoke-data/consumer-finance-complaints) |
| **Size** | 4.7M complaints in the source (2011 to Feb 2024). This repo ships a 2 MB aggregate: 2.83M complaints, 12 companies, Jan 2018 to Feb 2024 |
| **Shape** | `daily_counts(company, date, dimension, segment, count)`: daily volume overall, and split by product, issue, channel, company response, timeliness |
| **Labels** | Company response (explanation / monetary relief / non-monetary relief / in progress) and timely-response flag |
| **Events** | A small, editable table of real-world events (regulation, policy changes, incidents, launches). The product manager curates it |

Rebuild the snapshot from the full source: `python build_dataset.py` (downloads ~1.1 GB once).

### What a product manager should know about this data
- It is **complaints to a regulator**, not all support contacts: a skewed, unhappier sample.
- Credit bureaus (Equifax, Experian, TransUnion) are ~85% of the volume in this snapshot.
- Outcome fields are set by the company, and the newest complaints are still "In progress".
- The CFPB renamed products over time, so some "mix shifts" are artifacts.
- The newest days are excluded (still being published). Last complete day: 2024-02-15.

### Real anomalies in it (found by the tools, not yet explained)
- 2024-01-22: all three credit bureaus +150% to +170% together (about 1,500 vs about 600 a day), almost entirely web.
- 2023-01-20: Wells Fargo 1,213 vs a baseline of 44, 99% web, 68% checking/savings, no peer moved, no recorded event.

## 2. Assumptions

1. Metric = daily complaint volume per company.
2. Baseline = median of the same weekday over the previous 4 weeks. Anomaly = at least 15% off baseline.
3. Companies with fewer than 30 complaints on a typical day are skipped (small counts are noise).
4. The causes the agent may conclude are a fixed, editable list (Configure -> Causes). The default list is a
   starting hypothesis, **not** ground truth: sharpen it first.
5. Starter events are from public knowledge and unverified. Check them, then add your own.
6. Ground truth comes from a human grading the agent.

## 3. The dashboard (for product managers)

```bash
streamlit run app.py
```

| Page | What a PM does there |
|---|---|
| **Overview** | Monitor health, accuracy as you grade, tool calls per run, tokens, failures |
| **Run the agent** | Let it choose, pick an anomaly, or ask your own question. See every tool call it made |
| **Review & grade** | Confirm or correct its conclusions. This is the learning signal |
| **Memory** | Choose how memory is used, add your own lessons, delete bad ones, backup and restore |
| **Configure** | Edit the system prompt (versioned, with diff and rollback), enable or disable tools and rewrite their descriptions, set thresholds, edit the cause list, add saved SQL queries as tools, pick the model |
| **Data explorer** | Charts per company, breakdowns, anomalies, and **the events table where you add domain knowledge** |

API keys are typed in the sidebar and kept in the browser session only (never written to disk).
Set `APP_PASSWORD` to require a password on a public deployment. Agno telemetry is off by default.

## 4. How it works

```
build_dataset.py -> snapshot -> complaints.db -> tools.py (12 tools) -> runner.py (Agno agent) <- config.py
                                                                              |
                                      runs / investigations --+--> Review page --> lessons --> next run
```

**Why it is an agent:** it picks its own next tool call from what it finds, and stops when the evidence is
decisive, with a hard cap on tool calls.

**How it self-improves:** it logs a structured conclusion, a human grades it, the grade becomes a lesson, and
the lesson is in memory on the next run. Success looks like higher accuracy and fewer tool calls over time.

Guardrails: tools are read-only (single SELECT on a read-only connection); the agent can only write to its own
memory tables; conclusions are limited to the cause list; the tool-call cap is enforced by the framework.

## 5. Run it

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
streamlit run app.py               # dashboard (loads the shipped snapshot on first start)
python smoke_test.py               # tests every tool on the real data, no API key needed
python agent.py "Why did Wells Fargo complaints spike on 2023-01-20?"   # CLI, needs a model key
```

## 6. Deploy

Streamlit needs a Python server, so it cannot run on GitHub Pages (static files only). `render.yaml` deploys
it to Render. **Free hosting resets the disk on restart**, so lessons and settings are lost unless you use the
Memory page's backup/restore, or move to a paid plan with a disk (see `render.yaml`).

## 7. Status

- Dataset, tools, memory, the Agno agent, and the dashboard are built. Every tool, every page, and the
  run -> grade -> lesson loop were tested headlessly against the real data.
- The agent loop was tested with a **scripted fake model** (to verify the plumbing), not a real LLM.
  Whether a real model investigates *well* is untested until you run it with your key.
- No real investigations have been graded yet, so no improvement has been observed.
