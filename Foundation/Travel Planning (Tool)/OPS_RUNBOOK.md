# Ops Runbook — Travel Planning Agent
> Phase 5: Operate | Project: Travel Agent with Tool Use
> Run Environment: Streamlit (local)

---

## Section 1 — Security Checklist

### Critical — Do Before Pushing to GitHub

| Check | Status | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` is NOT hardcoded in `travel_agent_streamlit.py` | ☐ | Verify: grep the file for `sk-ant`; if found, move to env var immediately |
| `.env` file is listed in `.gitignore` | ☐ | Add `.env` to `.gitignore` before first commit |
| Streamlit `secrets.toml` (if used) is in `.gitignore` | ☐ | Path: `.streamlit/secrets.toml` — must not be committed |
| No API key in terminal/shell history from manual testing | ☐ | Run `history | grep sk-ant` to check; clear with `history -c` if found |
| Spend limit set in Anthropic Console | ☐ | Set a monthly hard limit at console.anthropic.com to prevent runaway costs |
| Streamlit app is not exposed to a public URL without auth | ☐ | Default `localhost:8501` is local only — safe; if deploying to Streamlit Cloud, add authentication |
| No user query data is logged to disk | ☐ | Current code uses no file writes — confirm no `print` → file redirects in your run command |

**Current pattern and fix:**

```python
# ❌ Current risk — if key is set in environment but not validated at startup
client = anthropic.Anthropic()  # Silently fails if key is missing; crashes on first API call

# ✅ Fix — validate at startup and fail fast with a clear message
import os
import sys
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY is not set. Export it before running.")
    sys.exit(1)
client = anthropic.Anthropic()
```

**How to set the key safely for local Streamlit runs:**
```bash
# Option 1: Export in terminal session (not persisted)
export ANTHROPIC_API_KEY="sk-ant-..."
python3 -m streamlit run travel_agent_streamlit.py

# Option 2: .env file + python-dotenv (persisted, gitignored)
# .env file:
# ANTHROPIC_API_KEY=sk-ant-...
```

---

## Section 2 — Prompt Injection Risk Assessment

**Overall risk: Low**

This agent accepts free-form text from the user, but the attack surface is narrow: all tool calls are hardcoded functions with no shell execution, database access, or file system writes. A malicious query can at most confuse Claude's tool selection — it cannot exfiltrate data or execute arbitrary code.

| Scenario | Risk level | Mitigation |
|---|---|---|
| User inputs a prompt designed to make Claude ignore the system prompt ("Ignore all previous instructions and...") | Low | Claude claude-sonnet-4-6 is robust to naive jailbreaks; tool schema constrains what actions are possible regardless |
| User crafts a query to extract the system prompt | Low | System prompt is a single benign sentence — no sensitive information to extract |
| User inputs a query designed to force all three tools to fire simultaneously with maximal tokens | Medium | Could inflate cost per query; mitigate with `max_tokens` cap (already set to 1000) |
| Malicious input passed through to real external APIs (in a future v2 with live tools) | High (future) | Validate and sanitise city/month inputs before passing to any external API in v2 |

---

## Section 3 — Cost Management

### Estimated Cost per Run

Based on `claude-sonnet-4-6` with a typical travel query that triggers 2 tool calls:

| Model | Input tokens (est.) | Output tokens (est.) | Cost per run |
|---|---|---|---|
| claude-sonnet-4-6 (current) | ~800 (system + history + tool results) | ~600 (synthesis response) | ~$0.005 per query |
| claude-haiku-4-5 (budget alternative) | ~800 | ~600 | ~$0.001 per query |

At current pricing, 1,000 queries on claude-sonnet-4-6 costs approximately $5.00. For a personal demo tool this is negligible; for a shared deployment, add rate limiting.

### Token Budget Controls

- **`max_tokens=1000`** limits the synthesis response — **confirmed in eval**: TC-03 (7-day Bali luxury plan) hit the ceiling and was truncated mid-sentence (`"Book villa and"`). Response was 3,032 chars — 3× the limit. Increase to 2000 immediately.
- **When to increase:** Already observed — TC-03 is a reproducible truncation case. Any query asking for a full itinerary + weather + budget will exceed 1000 tokens.
- **Cost optimisation:** Switch to `claude-haiku-4-5-20251001` for 80% cost reduction with acceptable quality for simple queries. Use claude-sonnet-4-6 only for complex multi-tool synthesis.

---

## Section 4 — Observability

### What you would log in production

| Event | What to Log | Why |
|---|---|---|
| Query received | timestamp, query length, session_id | Volume and session tracking |
| Tool call fired | tool_name, inputs, timestamp | Debug tool selection logic |
| Tool call result | result string, latency_ms | Detect stale or broken tool data |
| API response received | stop_reason, input_tokens, output_tokens, latency_ms | Cost tracking and truncation detection |
| Error | error_type, error_message, query_that_caused_it | Debug and alert on failures |

### What you can log right now (zero infrastructure)

Add this wrapper around the API call in `travel_agent_streamlit.py`:

```python
import time

def run_travel_agent(query, status_container):
    messages = [{"role": "user", "content": query}]
    total_input_tokens = 0
    total_output_tokens = 0
    start = time.time()

    while True:
        r = client.messages.create(...)
        total_input_tokens += r.usage.input_tokens
        total_output_tokens += r.usage.output_tokens

        if r.stop_reason == "end_turn":
            elapsed = round(time.time() - start, 2)
            print(f"[{elapsed}s] Tokens: {total_input_tokens} in / {total_output_tokens} out")
            # ... rest of function
```

This gives you latency and token counts per query in the terminal with no additional infrastructure.

---

## Section 5 — Known Limitations & Error Handling

| Limitation | Current behaviour | Better behaviour |
|---|---|---|
| Missing `ANTHROPIC_API_KEY` | Unhandled `AuthenticationError` crashes with a stack trace in the Streamlit UI | Catch at startup; display a clear in-UI error message: "API key not configured. Set ANTHROPIC_API_KEY." |
| Anthropic API timeout or rate limit | Unhandled exception surfaces as a red Streamlit error block | Wrap in try/except; display "The agent is temporarily unavailable — please try again." |
| Response truncated at `max_tokens=1000` | **Confirmed in eval (TC-03):** Response ends mid-sentence — observed cut-off: `"Book villa and"`. No UI warning shown. | Increase `max_tokens` to 2000; check `stop_reason == "max_tokens"` and append "⚠️ Response truncated — ask me to continue." |
| Agent calls unnecessary tools | **Confirmed in eval (TC-02, TC-05):** Agent called `estimate_budget` on a sightseeing-only query (TC-02) and `search_attractions` on a cost-only query (TC-05). Causes inflated responses and wasted tokens. | Strengthen system prompt: add "Only call tools that the user's question directly requires — do not call tools speculatively." |
| Agent adds unsourced context from training data | **Confirmed in eval (all TCs):** Agent supplements tool output with city-specific knowledge (landmarks, food, packing tips) not returned by any tool. Grounding risk in v2 when tools return real data that may contradict this. | Add to system prompt: "Only include information returned by tools. Do not add context from your training data." |
| Tool called with a travel style not in the enum | `estimate_budget` would fail if Claude inferred a style outside `["budget", "mid-range", "luxury"]` | Add input validation in `execute_tool`; default to "mid-range" with a note if style is unrecognised |
| Niche city returns incorrect data | **Confirmed in eval (TC-04):** `get_weather` returned "22-28°C, sunny" for Ulaanbaatar in January — factually wrong (actual: ~-20°C). Agent reported this as accurate. | Acceptable in v1 (simulated tools); flag in UI: "⚠️ Data is simulated — verify before planning." Priority fix in v2: replace `get_weather` with real API. |
| Session history grows unbounded in long conversations | Token count per API call grows with each turn; very long sessions will inflate costs and may hit context limits | Cap history at last N turns: `messages = messages[-10:]` before each API call |

---

## Section 6 — Feedback Loop

1. **After each run:** Check the terminal for token counts and latency. If a query takes >20s or uses >2000 input tokens, investigate — the session history may be growing too large.
2. **Eval baseline established (v1.0):** All five test cases scored — average 88.4/100, all pass. Weakest categories: Tool Selection (TC-02: 20/30, TC-05: 25/30) due to unnecessary tool calls. Weakest single result: TC-02 (77/100). See EVAL_SCORECARD.md Section 3.
3. **Priority fixes from eval:** (1) Increase `max_tokens` to 2000 — confirmed truncation on TC-03. (2) Tighten system prompt to suppress unnecessary tool calls — confirmed on TC-02 and TC-05. (3) Add training data leakage guard to system prompt — observed across all TCs.
4. **Iterate prompt:** Change one thing at a time. Log every change in `EVAL_SCORECARD.md` Section 5 (Prompt Iteration Log). The current system prompt is only one sentence — most quality improvements will come from prompt changes, not code changes.
5. **Compare versions:** Before and after any prompt change, run all five test cases from EVAL_SCORECARD.md and rescore each category. A change that improves TC-03 but breaks TC-02 is not net positive.

---

## Section 7 — Upgrade Roadmap

| Upgrade | What it adds | Complexity | Priority | Eval Evidence |
|---|---|---|---|---|
| Increase `max_tokens` to 2000 | Fixes confirmed truncation on complex queries | Low | **P0** | TC-03 truncated mid-sentence (confirmed) |
| Tighten system prompt — tool discipline | Stops unnecessary tool calls on simple queries | Low | **P0** | TC-02 called budget unprompted; TC-05 called attractions unprompted (confirmed) |
| Add `stop_reason == "max_tokens"` UI warning | Prevents silent truncation; user knows to ask to continue | Low | **P1** | TC-03 truncation gives no UI feedback (confirmed) |
| Add training data leakage guard to system prompt | Prevents ungrounded context being added to responses | Low | **P1** | All 5 TCs show unsourced city context added (confirmed) |
| Replace `get_weather` with OpenWeatherMap API | Real, current weather data — makes outputs trustworthy | Low | **P1** | TC-04 returned 22-28°C for Ulaanbaatar in January (confirmed wrong) |
| Add API key validation at startup | Prevents confusing crash; improves developer experience | Low | P2 | Predicted failure, not yet confirmed in eval |
| Replace `search_attractions` with Google Places API | Real, ranked attractions per city | Medium | P2 | All TCs return same 5 generic attractions (confirmed) |
| Cap session history to last 10 turns | Prevents unbounded token growth in long sessions | Low | P2 | Not yet observed in eval |
| Replace `estimate_budget` with live FX + cost-of-living API | Real budget estimates in user's currency | Medium | P3 | Hardcoded INR figures noted in scorecard |
| Add Streamlit auth for shared deployment | Prevents unauthorised API cost accumulation | Medium | P3 | Not yet deployed publicly |
| Add per-query token cost display in the UI | Transparency for users and cost awareness for the operator | Low | P3 | — |
| Migrate to FastAPI + React frontend | Supports concurrent users; enables production deployment | High | P4 | — |

---

## Section 8 — Next Level (First-Class Artifact)

> The most important upgrade to make this a stronger Level 3 agent — informed by predicted eval failures.

**Architectural upgrade:** Remain at Level 3 (ReAct loop) but ground it in real data — the pattern is correct, the tools are the gap. Replace all three simulated tool functions with real API integrations.

**One tool to add:** `get_weather` → OpenWeatherMap API (free tier). This is the highest-trust, lowest-complexity upgrade. Weather is the tool users are most likely to act on directly, and the simulated response is identical for every city.

**The eval that currently fails that this fixes:** TC-04 (Ulaanbaatar in January) — the simulated tool returns "22-28 degrees C, sunny" for one of the coldest cities on earth in winter. This is the most visible credibility failure in the current implementation.

**What this teaches for the next project:** Real tool integration introduces async complexity, rate limits, API key management per tool, and error handling for external service failures — the engineering concerns that separate a demo agent from a production one.

| Upgrade | Fixes | New complexity introduced | Eval status |
|---|---|---|---|
| Increase `max_tokens` to 2000 | TC-03 truncation failure — confirmed mid-sentence cut-off | Slightly higher cost per query (~2×); retest all TCs after | **Confirmed failure** |
| Tighten system prompt (tool discipline + grounding) | TC-02/TC-05 unnecessary tool calls; training data leakage in all TCs | Risk of over-constraining Claude on genuinely ambiguous queries | **Confirmed failure** |
| Add `stop_reason` check + UI warning | Silent truncation in TC-03 with no user feedback | Minor UI state management | **Confirmed failure** |
| Replace `get_weather` with real API | TC-04 weather credibility failure — 22-28°C for Ulaanbaatar in January | API key per tool; rate limiting; network error handling | **Confirmed failure** |

---

## Section 9 — Threat Model

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Anthropic API key leaked via git commit (e.g. hardcoded in script or left in notebook output) | Medium — common mistake for first-time API users | High — key can be used to rack up costs on the owner's account | Add pre-commit hook to scan for `sk-ant` strings; set spend limits in Anthropic Console |
| Runaway API costs from a shared deployment with no rate limiting | Low for local; Medium if deployed publicly | Medium — unexpected Anthropic bill | Set a hard monthly spend cap in Anthropic Console; add per-session query count limit in Streamlit |
| User submits a crafted query that consumes maximum tokens every turn | Low | Low-Medium — inflated cost, degraded experience for other users | Cap `max_tokens`; cap session history length; add query length limit in the UI input |
| Anthropic service outage causes Streamlit app to crash unhandled | Low-Medium (API services have SLAs but do go down) | Medium — app is completely unavailable; poor user experience | Wrap all API calls in try/except; display a graceful "Agent unavailable" message |
| User inputs personally identifiable information in a travel query (e.g. "I'm travelling with my child named...") | Medium — natural in a travel planning context | Low-Medium — data sent to Anthropic API; subject to their retention policy | Display a data notice in the UI; advise users not to include PII in queries |
