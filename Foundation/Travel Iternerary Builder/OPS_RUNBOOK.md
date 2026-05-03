# Ops Runbook — Travel Itinerary Builder
> Phase 5: Operate | Travel Itinerary Builder Agent
> Run Environment: Python script / Jupyter Notebook (local)
> Status: Complete

---

## Section 1 — Security Checklist

### Critical — Do Before Pushing to GitHub

| Check | Status | Notes |
|---|---|---|
| API key is loaded from environment variable, NOT hardcoded in the script | ☐ | See fix below — current code has a commented-out hardcoded key risk |
| `.env` file (if used) is listed in `.gitignore` | ☐ | Add `.env` to root `.gitignore` before first commit |
| No API key appears in any Jupyter notebook output cell | ☐ | Clear all outputs before committing: Kernel → Restart & Clear Output |
| No itinerary outputs saved to files containing user PII | ☐ | Current code prints to stdout only — verify no `open()` writes added |
| Anthropic spend limit set in dashboard | ☐ | Set a monthly cap at console.anthropic.com → Billing |
| Script not committed with a real user's travel request hardcoded | ☐ | Replace the example request with a generic placeholder before committing |

**Fix for API key handling:**

```python
# ❌ Current risk — commented-out pattern shows the anti-pattern
# os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

# ✅ Correct — load from environment only
import os
from dotenv import load_dotenv  # pip install python-dotenv

load_dotenv()  # reads from .env file if present
client = anthropic.Anthropic()  # auto-reads ANTHROPIC_API_KEY from environment
```

**.env file (do not commit):**
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**.gitignore entry:**
```
.env
*.env
__pycache__/
.ipynb_checkpoints/
```

---

## Section 2 — Prompt Injection Risk Assessment

**Overall risk: Low**

This agent runs locally, takes a single hardcoded request string, and sends it directly to the Anthropic API. There is no web interface, no user input field, and no untrusted external data ingested in v1.

| Scenario | Risk Level | Mitigation |
|---|---|---|
| Malicious travel request designed to leak the system prompt | Low | No secrets in system prompts; prompts are all publicly readable in the code |
| User crafts an input to override JSON format instructions in Parse step | Low | Only the developer sets the input string; not a public-facing tool in v1 |
| Research step receives injected instructions via a crafted destination name | Low | Destination is extracted from user input by Parse step — double-pass reduces risk |
| If extended to accept web form input (v2) | Medium | Would require input sanitisation: strip prompt injection markers, length-limit inputs |

**If this moves to a web-facing deployment:** Validate and sanitise all user inputs before passing to the chain. Add a maximum character limit (e.g. 500 chars) on the user request field. Log all inputs for audit purposes.

---

## Section 3 — Cost Management

### Estimated Cost per Run (5-day trip, standard inputs)

| Step | Model | Est. Input Tokens | Est. Output Tokens | Cost per Step* |
|---|---|---|---|---|
| Parse | claude-sonnet-4-5 | ~150 | ~80 | ~$0.0007 |
| Research | claude-sonnet-4-5 | ~200 | ~200 | ~$0.0018 |
| Schedule | claude-sonnet-4-5 | ~350 | ~300 | ~$0.0030 |
| Write | claude-sonnet-4-5 | ~400 | ~600 | ~$0.0046 |
| **Total** | | **~1,100** | **~1,180** | **~$0.010** |

*Based on Anthropic's current Sonnet pricing. Verify at anthropic.com/pricing.*

At current pricing, **100 runs costs approximately $1.00.** Cost scales roughly linearly with trip duration — a 10-day trip will approximately double the Schedule and Write token counts.

### Token Budget Controls

- **Current max_tokens per step:** 300 / 500 / 600 / 800
- **When to increase:** If TC-03 (14-day trip) truncates the schedule, raise the Schedule step to 1500 and the Write step to 1500.
- **When to decrease:** For a batch-generation use case (many short trips), lower Write to 500 to reduce cost by ~25%.
- **Cost optimisation model:** `claude-haiku-4-5` can run Parse and Research steps at 5–10x lower cost with minimal quality loss. Reserve Sonnet for Write step where prose quality matters most.

---

## Section 4 — Observability

### What You Would Log in Production

| Event | What to Log | Why |
|---|---|---|
| Chain start | timestamp, destination, duration, budget_level | Understand usage patterns; correlate with errors |
| Step completion | step_name, input_tokens, output_tokens, latency_ms | Track cost per step; identify which step is slowest |
| JSON parse success/failure | step_name, success=True/False, raw_output[:200] | Catch format breaks before they cascade |
| Chain completion | total_latency_ms, total_cost_usd, output_word_count | Top-level health metric |
| Error | step_name, error_type, error_message, input_hash | Diagnose failures without storing full user input |

### What You Can Log Right Now (no infrastructure needed)

Add this wrapper around each step call in your notebook:

```python
import time

def timed_step(name: str, fn, *args) -> str:
    start = time.time()
    result = fn(*args)
    elapsed = round((time.time() - start) * 1000)
    word_count = len(result.split())
    print(f"[{name}] {elapsed}ms | {word_count} words output")
    return result

# Usage:
parsed      = timed_step("Parse",    step_parse,    request)
experiences = timed_step("Research", step_research, parsed)
schedule    = timed_step("Schedule", step_schedule, parsed, experiences)
itinerary   = timed_step("Write",    step_write,    schedule)
```

This adds zero infrastructure and gives you per-step latency and output size tracking at a glance.

---

## Section 5 — Known Limitations & Error Handling

| Limitation | Current Behaviour | Better Behaviour |
|---|---|---|
| Missing API key | `anthropic.AuthenticationError` raised at first API call — Python traceback printed, no user-friendly message | Catch at startup: `if not os.environ.get("ANTHROPIC_API_KEY"): sys.exit("Error: ANTHROPIC_API_KEY not set")` |
| API timeout or network error | Unhandled exception crashes the script mid-chain | Wrap each step in try/except with a retry (max 2 retries with 2s backoff) and a clear error message |
| Parse step returns prose instead of JSON | `step_research` receives free text — likely produces garbled or hallucinated experiences | Wrap parse output in try/except json.loads(); if it fails, retry Parse once with a stricter prompt |
| Schedule step JSON truncated (long trips) | JSON ends mid-object; write step receives broken input and produces garbled prose | Check if output ends with `}` before passing to write; if not, alert and ask user to reduce trip length or increase max_tokens |
| Niche destination produces hallucinated experience | Final itinerary includes a venue that doesn't exist | Add disclaimer to every output: "Verify all experiences exist before booking." Long-term: add web search grounding |
| Rate limit hit (many runs in quick succession) | `anthropic.RateLimitError` crashes the chain | Add exponential backoff with max 3 retries; print a user-friendly "Rate limited — retrying in Xs" message |

---

## Section 6 — Feedback Loop

How to improve the agent over time running locally:

1. **After each run:** Check the Parse JSON output — does it correctly capture all 4 fields from your input? This is the most fragile step. If it adds extra fields or misreads budget level, note the input that triggered it.

2. **After 5 runs:** Review the experience lists. Are the same 3–4 "generic tourist" experiences appearing for every destination? This indicates the Research system prompt is too vague. Note which destinations surface weak or hallucinated experiences.

3. **Iterate one prompt at a time:** Change exactly one system prompt or user prompt, re-run all 5 test cases from `EVAL_SCORECARD.md`, and compare scores before and after. Log every change in a `PROMPT_LOG.md` file with the date, change, and score delta.

4. **Compare versions:** Before promoting any prompt change, run TC-01 through TC-05 with both the old and new prompt. If average score improves by ≥5 points without any category dropping below the 50% floor, adopt the change.

---

## Section 7 — Upgrade Roadmap

| Upgrade | What It Adds | Complexity | Priority |
|---|---|---|---|
| Web search on Research step | Live experience data; reduces hallucinations on niche destinations | Medium | High |
| JSON validation between each step | Catches format breaks before they cascade; graceful error messages | Low | High |
| Haiku for Parse + Research steps | 5–10x cost reduction with minimal quality loss on structured steps | Low | Medium |
| Output disclaimer appended to final itinerary | Reminds users to verify prices and hours; reduces trust damage from stale data | Low | Medium |
| Streamlit UI | Non-technical users can type their trip request in a web form | Medium | Medium |
| Session state + revision workflow | User can ask "change Day 2 to include more food" without rerunning the full chain | High | Low |
| RAG over curated travel knowledge base | Grounded, up-to-date destination knowledge without live API calls | High | Low |
| Multi-destination routing (Level 3) | Plan a trip across multiple cities with logical routing between them | High | Low |

---

## Section 8 — Next Level (First-Class Artifact)

**Architectural upgrade:** Level 2 (prompt chain) → Level 3 (ReAct loop with tool use)

**One tool to add:** `web_search` integrated into the Research step — the agent fetches live TripAdvisor, Google Places, or Lonely Planet data before generating the experience list, grounding every recommendation in current, real-world data.

**The eval that currently fails that this fixes:** TC-04 (Tbilisi, Georgia — niche destination). The Research step currently relies entirely on LLM training data, which is thin for less-common destinations. Web search would surface real, current experiences rather than plausible-sounding hallucinations.

**What this teaches for the next project:** Tool use transforms a fixed pipeline into a dynamic reasoner — the agent now decides *when* to search, *what* to search for, and *how* to incorporate the result. This is the core skill of ReAct agent design.

| Upgrade | Fixes | New Complexity Introduced |
|---|---|---|
| Web search on Research step | TC-04 niche destination hallucination; stale pricing in any TC | Tool call error handling; result parsing; rate limits on search API |
| JSON validation step between Parse → Research | TC-05 stress test crash from malformed parse output | Additional API call cost; slightly increased latency |
| Retry loop on Parse step | TC-05 format failures; any input that confuses the LLM | Loop termination logic; max-retry handling; cost increase on retries |

---

## Section 9 — Threat Model

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| API key committed to a public GitHub repo | Medium — common mistake when copying code from notebook to repo | High — key is compromised immediately; billed charges from unauthorised use | Add `.env` to `.gitignore` before first commit; rotate key immediately if exposed; enable spend alerts |
| Hallucinated venue causes user to travel to a non-existent location | Medium — higher for niche destinations; lower for popular cities | Medium — wasted travel time; trust damage | Add output disclaimer; upgrade Research step to web search grounding in v2 |
| Token cost overrun on accidental long-trip batch run | Low — script runs one request at a time; no automation | Low — at ~$0.01/run, cost is negligible for individual use | Set a monthly spend cap in the Anthropic dashboard; add a duration_days sanity check before running |
| Prompt chain producing biased destination recommendations | Low — not intentional, but LLM training data has geographic and cultural biases | Low — user receives a skewed experience list | Evaluate outputs across diverse destinations during Phase 4; note systematic gaps in the eval scorecard |
| API downtime breaking the chain mid-run | Low — Anthropic API has high uptime | Low — user must re-run; no data is lost | Add retry logic with backoff; print which step failed so user can resume manually if needed |
