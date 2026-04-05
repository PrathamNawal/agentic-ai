# Design Document — AI Travel Planner
> Phase 2: Design | Foundation Project #01

---

## 1. Agent Architecture Classification

| Dimension | This Agent | Why |
|---|---|---|
| **Pattern** | Single LLM call (prompt chain) | No loop, no tool invocation, no decision branching |
| **Memory** | None (stateless) | Each run is independent; no history retained |
| **Tools** | None | No external APIs called by the LLM itself |
| **Autonomy level** | Level 1 — Deterministic pipeline | User controls all inputs; agent executes once |
| **Upgrade path** | Level 2 would add web search tool for live data |  |

> **PM Note:** Understanding where your agent sits on the autonomy spectrum is critical for scoping, risk assessment, and user expectation setting.

---

## 2. Architecture Decision

> The most consequential design decision for any agent. Answer this before touching workflow or config: **what is the minimum autonomy level needed to solve this problem?**

| Level | Pattern | Description | This agent? |
|---|---|---|---|
| 1 | Single LLM call | One prompt in, one response out. No loops, no tools. | ✅ Yes — sufficient for structured itinerary generation |
| 2 | Prompt chain | Multiple sequential LLM calls, output of one feeds next | Not needed for v1 |
| 3 | ReAct loop | LLM reasons, picks a tool, observes result, repeats | Needed when adding live web search |
| 4 | Multi-agent | Orchestrator delegates to specialist agents | Needed for booking + planning separation |

**Decision: Level 1 is the right choice for this agent because:**
- The problem is well-defined and bounded (fixed inputs → structured output)
- No real-time data is required for a planning-only tool
- User tolerance for error is moderate (they verify before booking)
- Complexity should match the learning objective: understand single LLM calls before loops

**When to upgrade:** The moment a user says "but are these restaurants actually open?" — that's the signal to move to Level 3 with a web search tool.

---

## 3. Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INPUTS (Cell 3)                         │
│   destination · num_days · budget · interests · companions · date   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PROMPT BUILDER (Cell 4)                           │
│                                                                     │
│  ┌──────────────────────────────┐  ┌────────────────────────────┐  │
│  │       SYSTEM PROMPT          │  │       USER PROMPT           │  │
│  │  Role: Expert travel agent   │  │  Destination: New Delhi     │  │
│  │  Format: Day X - Location    │  │  Days: 5 | Budget: luxury   │  │
│  │  Rules: specific venues,     │  │  Interests: food, culture   │  │
│  │  budget-aware, realistic     │  │  Companions: couple         │  │
│  └──────────────────────────────┘  └────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   OPENROUTER API CALL                               │
│   Model: openai/gpt-4o-mini                                         │
│   Temperature: 0.7 | Max tokens: 2000 | Timeout: 30s               │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   LLM RESPONSE (raw text)                           │
│   "Day 1 - New Delhi\n- Activity...\nDay 2 - New Delhi\n..."        │
└──────────┬────────────────────────────────────────┬────────────────┘
           │                                        │
           ▼                                        ▼
┌──────────────────────────┐            ┌───────────────────────────┐
│  MARKDOWN RENDER (Cell 5)│            │  ICS PARSER (Cell 6)      │
│  display(Markdown(...))  │            │  regex split on "Day \d+" │
│  Rich itinerary in       │            │  → Calendar Event per day  │
│  Jupyter notebook        │            │  → .ics file export        │
└──────────────────────────┘            └───────────────────────────┘
                                                    │
                                                    ▼
                                        ┌───────────────────────────┐
                                        │  USER DOWNLOADS .ics      │
                                        │  Imports to Google /      │
                                        │  Apple / Outlook Calendar │
                                        └───────────────────────────┘
```

---

## 4. Agent Configuration Sheet

### 3a. Model Parameters

| Parameter | Value | Rationale |
|---|---|---|
| **Model** | `openai/gpt-4o-mini` via OpenRouter | Fast, cheap, strong instruction-following for structured output |
| **Temperature** | `0.7` | Balanced — some creativity in activity suggestions, but not hallucination-prone |
| **Max tokens** | `2000` | Sufficient for 5-7 day itinerary; increase to 3000 for 10+ day trips |
| **Timeout** | `30s` | Safe buffer for API response; avoids hanging notebooks |
| **Top-p** | Not set (default ~1.0) | Temperature is the primary control here |
| **Frequency penalty** | Not set | Could add 0.3 to reduce repetitive activity suggestions |

> **When to change temperature:** Drop to 0.3 if you want more factual, consistent outputs (e.g., business travel). Raise to 0.9 for more adventurous, varied suggestions. Never go above 1.0 for structured output tasks.

---

### 3b. Prompt Architecture

**System Prompt Role:** Sets the agent's persona and enforces output format

```
You are an expert travel agent specialising in personalised travel itineraries.
Format: Day X - [City/Area]\n- Activity 1\n- Activity 2...
Rules: Specific venues, budget-aware, realistic travel time
```

**User Prompt Role:** Provides the specific trip parameters

```
{num_days}-day itinerary for {destination}
Budget: {budget} | Interests: {interests} | Companions: {companions}
Include: iconic attractions, hidden gems, dining, local experiences
```

**Format constraint (critical):** The system prompt forces a regex-parseable structure (`Day \d+`). This is what makes the ICS export work. If the format breaks, the calendar export fails.

---

### 3c. Memory Configuration

| Memory Type | Used? | Notes |
|---|---|---|
| In-context (conversation history) | No | Single-shot call only |
| Vector / RAG | No | No external knowledge base |
| External DB | No | No persistence between runs |
| Session state | No | Each notebook run is fresh |

**Upgrade path:** Adding short-term memory (conversation history) would allow the user to refine the itinerary conversationally ("make Day 2 more relaxed", "swap the restaurant on Day 3").

---

### 3d. Tools Configuration

| Tool | Used? | Notes |
|---|---|---|
| Web search | No | LLM relies on training data only |
| Maps / distance API | No | Travel time is estimated by LLM heuristic |
| Booking APIs | No | Planning only, no transactions |
| Calendar API | Partial | Local `.ics` generation — not OAuth-connected |

**Upgrade path:** Adding a Tavily/SerpAPI web search tool would make this a true agentic system — the LLM could search for current venue hours, real prices, and recent reviews before building the itinerary.

---

## 5. Data Flow & Security Notes

- API key stored in plaintext in notebook cell — **never commit to GitHub with real key**
- No user data is stored or logged
- All LLM calls go via OpenRouter (third-party) — check their data retention policy
- `.ics` file is written to local disk — no cloud upload

---

## 6. Data Grounding & Freshness

| Dimension | Detail |
|---|---|
| **Data source** | GPT-4o-mini training data (no live retrieval) |
| **Knowledge cutoff** | Model cutoff applies — venues may have closed, prices changed, hours shifted |
| **Grounding method** | None in v1 — output is entirely LLM-generated, not verified against live sources |
| **Freshness risk** | High for fast-changing info (restaurants, hotels); low for landmarks and monuments |
| **Mitigation** | Add disclaimer in output; user must verify before booking |
| **Upgrade path** | Add Tavily/SerpAPI web search so agent retrieves live data before generating itinerary |

---

## 7. Eval Success Definition (Pre-Build)

> Written now, before code exists. Full scoring happens in Phase 4.

| Criterion | What "good" looks like |
|---|---|
| Format compliance | Every day parsed correctly; calendar events = num_days |
| Budget alignment | Luxury → 5-star hotels, fine dining. Low → hostels, street food. No crossover. |
| Interest match | At least 70% of activities map to stated interests |
| Geographic logic | Day's activities cluster by area — no unnecessary cross-city travel |
| Specificity | Real venue names used, not generic ("a nice restaurant") |

**Minimum bar for v1 to be considered working:** Format compliance 100%, overall score ≥ 70/100 across 5 test cases.

