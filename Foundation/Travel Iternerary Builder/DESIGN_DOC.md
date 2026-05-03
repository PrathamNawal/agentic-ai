# Design Document — Travel Itinerary Builder
> Phase 2: Design | Travel Itinerary Builder Agent
> Status: Complete

---

## Section 1 — Agent Architecture Classification

| Dimension | This Agent | Why |
|---|---|---|
| Pattern | Prompt chain (Level 2) | Task decomposes cleanly into 4 sequential steps with no branching or tool decisions needed |
| Memory | None | Each step receives all context it needs via function arguments; no cross-session state required |
| Tools | None in v1 | Knowledge from LLM training data is sufficient for popular destinations; live data is a v2 upgrade |
| Autonomy level | Level 2 — sequential prompt chain | The agent does not make decisions about which tools to call or whether to loop; it follows a fixed pipeline |
| Upgrade path | Level 3: add a web search tool to the Research step; add a validation loop that checks JSON format before proceeding |

---

## Section 2 — Architecture Decision

| Level | Pattern | Description | This agent? |
|---|---|---|---|
| 1 | Single LLM call | One prompt in, one response out | ❌ |
| 2 | Prompt chain | Sequential calls, output feeds next | ✅ |
| 3 | ReAct loop | LLM reasons, picks tool, observes, repeats | ❌ |
| 4 | Multi-agent | Orchestrator delegates to specialists | ❌ |

- **Why Level 2 is right:** The problem decomposes into four well-defined, sequential subtasks (parse → research → schedule → write), each with a clear input and output. No dynamic branching, tool selection, or retry logic is needed in v1.
- **What would require going higher:** If the agent needed to check live prices, validate experiences against a booking API, or adapt the schedule based on real-time availability, Level 3 (ReAct) would be required.
- **What complexity this avoids:** No tool orchestration, no loop termination logic, no partial state management — the pipeline runs in a straight line, which makes it debuggable, cheap, and fast to iterate.

---

## Section 3 — Workflow Diagram

```
┌─────────────────────────────────────┐
│           USER INPUT                │
│  "5 days in Kyoto, Japan.           │
│   I love temples and food.          │
│   Mid-range budget."                │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│         STEP 1: PARSE               │
│  System: "Extract travel details.   │
│           Return JSON only."        │
│  Output: {destination, duration,    │
│           travel_style, budget}     │
└──────────────────┬──────────────────┘
                   │  parsed JSON
                   ▼
┌─────────────────────────────────────┐
│         STEP 2: RESEARCH            │
│  System: "Travel researcher.        │
│           Top 5 must-do             │
│           experiences as JSON."     │
│  Input:  parsed profile             │
│  Output: [{name, duration_hours,    │
│            cost_level}, ...]        │
└──────────────────┬──────────────────┘
                   │  experience list
                   ▼
┌─────────────────────────────────────┐
│         STEP 3: SCHEDULE            │
│  System: "Travel planner.           │
│           Day-by-day schedule."     │
│  Input:  parsed + experiences       │
│  Output: {day_1: [...],             │
│            day_2: [...], ...}       │
└──────────────────┬──────────────────┘
                   │  schedule JSON
                   ▼
┌─────────────────────────────────────┐
│         STEP 4: WRITE               │
│  System: "Travel writer.            │
│           Engaging, practical       │
│           itinerary prose."         │
│  Input:  schedule JSON              │
│  Output: Markdown narrative         │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│         FINAL OUTPUT                │
│  Printed: parsed, experiences,      │
│           schedule, itinerary       │
└─────────────────────────────────────┘
```

---

## Section 4 — Agent Configuration Sheet

### 4a. Model Parameters

| Parameter | Value | Rationale |
|---|---|---|
| Model | claude-sonnet-4-5 (Anthropic) | Strong instruction-following and JSON output; good balance of quality and speed for this pipeline |
| Temperature | 0.3 (parse/schedule) / 0.7 (research/write) | Parse and schedule need deterministic structure; research and writing benefit from creative variety |
| Max tokens — Parse | 300 | JSON object with 4 fields; 300 is sufficient with headroom |
| Max tokens — Research | 500 | JSON list of 5 experiences; 500 supports detailed entries |
| Max tokens — Schedule | 600 | Day-by-day JSON for up to 7 days; 600 is tight for longer trips |
| Max tokens — Write | 800 | Prose narrative; 800 yields 500–600 words, suitable for a readable itinerary |
| Timeout | 30s per step | Generous for synchronous calls; adjust upward for longer trips |
| Top-p | Default | Temperature is the primary creativity control; top-p not needed |

> **When to change temperature:** Lower temperature to 0.1 on Parse if JSON deviations are observed (hallucinated extra fields). Raise temperature to 0.9 on Write if outputs feel formulaic across different destinations. Leave Research at 0.7 to encourage surfacing of non-obvious experiences.

---

### 4b. Prompt Architecture

**Step 1 — Parse**

System Prompt Role: Enforce strict JSON extraction from free-form natural language input.
```
Extract travel details. Return JSON only, no markdown.
```

User Prompt Role: Provide the raw user input and name the fields to extract.
```
Extract: destination, duration_days, travel_style, budget_level from: {user_request}
```

**Critical constraint:** The system prompt must explicitly say "Return JSON only, no markdown" — any deviation (prose, backticks, explanation) will break the downstream steps which assume parseable JSON.

---

**Step 2 — Research**

System Prompt Role: Focus the model on the role of a travel researcher, outputting a list not prose.
```
You are a travel researcher. Return JSON list of top 5 must-do experiences only.
```

User Prompt Role: Inject the parsed profile and specify the required output schema.
```
Based on this trip profile: {parsed}
List top 5 experiences with name, duration_hours, cost_level.
```

**Critical constraint:** "Return JSON list only" in the system prompt prevents the model from adding narrative framing that would break the schedule step.

---

**Step 3 — Schedule**

System Prompt Role: Prime the model for logical, practical trip planning with geographic awareness.
```
You are a travel planner. Create a logical day-by-day schedule.
```

User Prompt Role: Provide both the trip profile (for constraints) and the experience list (for content).
```
Trip profile: {parsed}
Available experiences: {experiences}
Create a day-by-day schedule as JSON.
```

**Critical constraint:** Both the parsed profile (for duration, budget) and the experiences list must be passed together — the model cannot infer duration from the experience list alone.

---

**Step 4 — Write**

System Prompt Role: Shift tone to warm, practical travel writing.
```
You are a travel writer. Write an engaging, practical itinerary.
```

User Prompt Role: Pass the schedule as the single source of truth for content.
```
Convert this schedule into a friendly, detailed travel itinerary:
{schedule}
```

**Critical constraint:** The write step has no constraints on format — this is the only step where markdown, prose, and structure are all acceptable. Do not add "return JSON only" here.

---

### 4c. Memory Configuration

| Memory Type | Used? | Notes |
|---|---|---|
| In-context (conversation history) | No | Each step is a fresh API call; context is passed explicitly via function arguments |
| Vector / RAG | No | All knowledge from LLM training data |
| External DB | No | No persistence between runs |
| Session state | No | Pipeline is stateless; each run is independent |

**Upgrade path:** Adding session state (e.g. storing the final itinerary in a dict keyed by user ID) would allow the agent to support a revision workflow — "change Day 2 to include more food options" — without rerunning the full chain.

---

### 4d. Tools Configuration

| Tool | Used? | Notes |
|---|---|---|
| Web search | No | Highest-value v2 upgrade — adds live review data to the Research step |
| Google Maps API | No | Would enable geographic clustering in the Schedule step |
| Booking.com / Viator API | No | Would add real pricing and booking links to the output |
| JSON validator | No | Would catch parse errors before they propagate downstream |

**Upgrade path:** Adding web search to Step 2 (Research) is the single highest-value tool addition — it grounds the experience list in current data and dramatically reduces hallucination risk on niche destinations.

---

## Section 5 — Data Flow & Security Notes

- **API key:** Loaded from `os.environ["ANTHROPIC_API_KEY"]`. If hardcoded in the notebook and committed to GitHub, it will be exposed and compromised. Use `.env` files or environment variables exclusively.
- **User data sent externally:** The raw user request, all intermediate JSON outputs, and the final itinerary are sent to Anthropic's API. No PII is collected by this agent, but if users describe medical needs or personal situations in their request, that text is transmitted.
- **Written to disk:** Nothing is written to disk in v1 — all outputs are printed to stdout. No log files or output files are created.
- **Third-party data retention:** Anthropic's API data retention policies apply to all messages sent. Review the Anthropic privacy policy for current retention terms.

---

## Section 6 — Data Grounding & Freshness

| Dimension | Detail |
|---|---|
| Data source | Claude Sonnet LLM training data — broad travel knowledge up to training cutoff |
| Knowledge cutoff | New restaurants, closed venues, changed entry requirements, and new attractions after cutoff will not appear |
| Grounding method | None in v1 |
| Freshness risk | **Medium** — foundational experiences (major temples, cuisine neighbourhoods, historic districts) are stable; specific restaurant recommendations and pricing are high-risk |
| Mitigation | Add a disclaimer in the final output: "Verify opening hours, prices, and availability before booking. This itinerary is based on LLM training data and may not reflect recent changes." |
| Upgrade path | Add the `web_search` tool to Step 2 (Research) to fetch live TripAdvisor or Google Places data before generating the experience list |

---

## Section 7 — Eval Success Definition (Pre-Build)

> Written before running evals. Full scoring in Phase 4 Eval Scorecard.

| Criterion | What "good" looks like |
|---|---|
| Parse accuracy | The parsed JSON contains all 4 required fields with correct values matching the user's input; no hallucinated extra fields |
| Experience relevance | At least 4 of the 5 listed experiences clearly match the stated travel style (e.g. temple-focused for "temples and food") |
| Schedule logic | Activities are grouped by proximity; no day is overloaded (more than 12 hours of activity); the number of days matches `duration_days` |
| Itinerary completeness | Final prose covers every day in the schedule; includes practical information (timing, rough cost level) |
| Format stability | All 3 intermediate JSON outputs parse without error when passed to the next step |

**Minimum bar for v1:** The agent must produce a final itinerary that covers the correct destination, correct number of days, and at least 3 activities relevant to the user's stated interests — without crashing or producing empty output.

---

## Section 8 — Excalidraw Diagram Notes

**Colour coding:**
- Blue boxes: User-facing steps (input prompt, final output)
- Yellow boxes: LLM processing steps (Parse, Research, Schedule, Write)
- Green arrows: JSON data flowing between steps
- Orange annotation: "Format-critical path" on Parse → Research → Schedule arrows (JSON format must hold at these transitions)

**Arrow labels:**
- User → Parse: "raw natural language"
- Parse → Research: "structured JSON (4 fields)"
- Research → Schedule: "experience list JSON"
- Parse → Schedule: "trip profile JSON" (parallel arrow — both inputs required)
- Schedule → Write: "day-by-day JSON"
- Write → User: "prose itinerary"

**Grouping:**
- Group Parse + Research + Schedule in a "Chain Engine" box
- Keep Write separate — it's a presentation layer, not a reasoning step

**Special annotation:**
- Flag the Parse → Research transition: "This is where format breaks cascade — if Parse returns prose instead of JSON, all downstream steps fail"
