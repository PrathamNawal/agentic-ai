# Ops Runbook — AI Travel Planner
> Phase 5: Operate | Foundation Project #01

---

## 1. Security Checklist

### Critical — Do Before Pushing to GitHub

| Check | Status | Notes |
|---|---|---|
| API key is NOT hardcoded in committed notebook | ✅ | Using `os.environ.get("OPENROUTER_API_KEY")` |
| `.env` file is in `.gitignore` | ✅ | Added |
| `travel_itinerary.ics` is in `.gitignore` | ✅ | Added |
| No real API key in notebook output cells | ✅ | Outputs cleared before commit |
| OpenRouter key has usage limits set | ✅ | Monthly spend cap set in OpenRouter dashboard |

**Recommended fix for API key:**
```python
# Instead of: OPENROUTER_API_KEY = "sk-or-..."
# Use this:
import os
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
if not OPENROUTER_API_KEY:
    print("⚠️  Set OPENROUTER_API_KEY environment variable")
```

---

## 2. Prompt Injection Risk

**Risk level for this agent: Low**

This agent does not accept free-form user text input from untrusted sources — all inputs are structured fields (destination, budget, etc.). However:

| Scenario | Risk | Mitigation |
|---|---|---|
| User types malicious text in `destination` field | Low — goes into user prompt only | Validate input is a plausible place name |
| If agent is ever exposed as an API endpoint | Medium | Add input sanitisation before passing to prompt |
| LLM recommends real venues that no longer exist | Low-medium | Add disclaimer in output |

---

## 3. Cost Management

### Estimated Cost per Run

| Model | Input tokens (est.) | Output tokens (est.) | Cost per run |
|---|---|---|---|
| GPT-4o-mini via OpenRouter | ~300 | ~700 | ~$0.0002 |
| GPT-4o via OpenRouter | ~300 | ~700 | ~$0.006 |

**At current pricing, 1000 runs of this agent costs less than $0.25 with gpt-4o-mini.**

### Token Budget Controls
- `max_tokens: 2000` — ✅ implemented, hard cap on output length
- For 10+ day trips, increase to `3000` to avoid cut-off itineraries
- For cost optimisation, could drop to `gpt-3.5-turbo` for low-budget trips

---

## 4. Observability (What to Log)

✅ **Implemented** via Cell 4b wrapper — latency and estimated output tokens logged on every run.

| Event | What to Log | Status |
|---|---|---|
| API call made | timestamp, destination, model, token count | ⬜ Not yet |
| API response received | latency, estimated output tokens | ✅ Implemented |
| Format parse result | days parsed, events created | ⬜ Not yet |
| ICS export | filename, event count, any parse errors | ⬜ Not yet |
| Error | error type, message, input that caused it | ⬜ Not yet |

**What's running now (Cell 4b):**
```python
import time, tiktoken

_original = generate_itinerary

def generate_itinerary(destination, num_days, budget, interests, companions):
    start = time.time()
    result_text = _original(destination, num_days, budget, interests, companions)
    latency = round(time.time() - start, 2)
    enc = tiktoken.encoding_for_model("gpt-4o-mini")
    tokens_out = len(enc.encode(result_text))
    print(f"⏱ Latency: {latency}s | Output tokens: {tokens_out}")
    return result_text

print("✓ Observability wrapper active")
```

**Note:** Input token count is not captured (would require returning `result` from Cell 4). Output tokens are counted via `tiktoken` — exact on the output side. To get full token usage in future, return `itinerary, result` from `generate_itinerary()` in Cell 4.

---

## 5. Known Limitations & Handling

| Limitation | Current behaviour | Better behaviour |
|---|---|---|
| API key missing | Prints warning, proceeds and fails | Halt execution immediately with clear message |
| API timeout (>30s) | Raises RequestException, returns error string | Retry once with backoff, then surface error |
| API rate limit hit | Returns HTTP 429 error in string | Parse error code and show specific message |
| Empty/malformed response | Crashes on `result["choices"][0]` | Wrap in try/except with fallback message |
| ICS parse fails | Silent — creates 0 events | Print count of events created for verification |

---

## 6. Feedback Loop (How to Improve Over Time)

Since this agent runs locally (no user telemetry), feedback is manual. Build this habit:

1. **After each run:** Score it on the Eval Scorecard
2. **After 5 runs:** Review failure patterns — what's consistently wrong?
3. **Iterate prompt:** One change at a time. Log in the Prompt Iteration Log (Evals doc)
4. **Compare versions:** Run all 5 test cases before and after any prompt change

---

## 7. Upgrade Roadmap

What would make this a more capable (Level 2+) agent:

| Upgrade | What it adds | Complexity |
|---|---|---|
| Add Tavily web search tool | Live venue hours, real reviews, current prices | Medium |
| Add multi-turn conversation | User can refine itinerary interactively | Medium |
| Add Maps API for travel time | Realistic day sequencing by geography | Medium |
| Add Streamlit UI | No Jupyter needed — browser-based | Low |
| Add vector memory | Remember user preferences across trips | High |
| Add booking tool | Actually purchase tickets/hotels | Very High |

---

## 9. Next Level — Upgrade to Level 2 Agent

> Written after evals. The one upgrade that would fix the most failing eval criteria.

**Architectural upgrade:** Move from Level 1 (single LLM call) to Level 3 (ReAct loop with tools)

**One tool to add:** Tavily web search — lets the LLM retrieve live venue hours, recent reviews, and current prices before generating the itinerary

**The eval that currently fails that this fixes:** Output relevance for niche destinations scores poorly because the LLM has sparse training data. Web search grounds every recommendation in live reality.

**What this teaches for the next project:** How to give an LLM a tool, handle tool call results, and feed observations back into the reasoning loop — the core of all agentic systems.

| Upgrade | Fixes | New complexity introduced |
|---|---|---|
| Add Tavily web search | Hallucinated/closed venues, niche destination gaps | Tool call handling, result parsing, longer latency |
| Add multi-turn conversation | Single-shot limitation, no refinement possible | Conversation state management, context window growth |
| Add Streamlit UI | Jupyter dependency, non-technical user barrier | Frontend deployment, session management |

---

## 10. Threat Model

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| API key leaked via GitHub | High (if not careful) | Medium (charges on your account) | .gitignore + env vars |
| LLM hallucinates fake venues | Medium | Low (user checks before booking) | Add disclaimer in output |
| Prompt injection via destination field | Low | Low (local tool) | Input validation |
| OpenRouter outage | Low | High (agent breaks) | Add fallback model or error message |
| Cost overrun | Low (cheap model) | Low | Set spend cap in OpenRouter dashboard |
