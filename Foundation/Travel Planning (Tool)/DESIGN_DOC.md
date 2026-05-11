# Design Document — Travel Planning Agent
> Phase 2: Design | Project: Travel Agent with Tool Use
> Status: Complete — pre-build design for Streamlit implementation

---

## Section 1 — Agent Architecture Classification

| Dimension | This Agent | Why |
|---|---|---|
| Pattern | ReAct loop (Level 3) | User queries are open-ended; the agent must decide which tools to call based on query intent — no hardcoded routing works |
| Memory | In-context only (session-scoped) | Chat history is held in `st.session_state.messages`; resets on page reload — no cross-session memory needed for v1 |
| Tools | 3 tools: `get_weather`, `search_attractions`, `estimate_budget` | Each covers a distinct user information need; Claude selects the right subset per query |
| Autonomy level | Level 3 — ReAct loop | LLM reasons about tool selection, executes tools iteratively, and synthesises results before responding |
| Upgrade path | Level 4 (Multi-agent) would add a Planner agent that breaks complex itineraries into sub-tasks delegated to specialist agents |

---

## Section 2 — Architecture Decision

| Level | Pattern | Description | This agent? |
|---|---|---|---|
| 1 | Single LLM call | One prompt in, one response out | ❌ |
| 2 | Prompt chain | Sequential calls, output feeds next | ❌ |
| 3 | ReAct loop | LLM reasons, picks tool, observes, repeats | ✅ |
| 4 | Multi-agent | Orchestrator delegates to specialists | ❌ |

- **Why Level 3 is right:** Travel queries are ambiguous and varied — "Plan a trip to Bangkok" might require all three tools, while "What's Kyoto famous for?" may only need `search_attractions`. A ReAct loop lets Claude dynamically decide; a prompt chain would require hardcoding every possible query type.
- **What would require going higher:** Level 4 would be justified if users asked for full multi-destination itineraries requiring parallel research agents, or if specialist agents were needed for flight search, accommodation, and activities separately.
- **What complexity this avoids:** We are not building a prompt chain (which would require predefined branching logic), a vector DB (no unstructured knowledge to retrieve), or a multi-agent orchestrator (single user intent per query is sufficient for v1).

---

## Section 3 — Workflow Diagram

```
┌─────────────────────────────────┐
│         User (Browser)          │
│  Types query in Streamlit chat  │
└────────────────┬────────────────┘
                 │ Natural language query
                 ▼
┌─────────────────────────────────┐
│       Streamlit App Layer       │
│  - Appends to session messages  │
│  - Renders chat history         │
│  - Shows live tool call status  │
└────────────────┬────────────────┘
                 │ messages[] + tools[]
                 ▼
┌─────────────────────────────────┐
│     Claude claude-sonnet-4-6 (Anthropic)    │
│  System prompt: travel assistant│
│  Reasons: which tools to call?  │
└──────┬──────────────────────────┘
       │ stop_reason == "tool_use"
       ▼
┌─────────────────────────────────┐     ┌──────────────────────────┐
│       Tool Dispatcher           │────▶│     get_weather()        │
│  Iterates r.content blocks      │     │  Returns: temp, season   │
│  Calls execute_tool() per block │────▶│  search_attractions()    │
│  Appends tool_results[]         │     │  Returns: top 5 places   │
└──────┬──────────────────────────┘────▶│  estimate_budget()       │
       │                                │  Returns: INR/day figure │
       │ tool_results appended          └──────────────────────────┘
       │ to messages[]
       ▼
┌─────────────────────────────────┐
│     Claude claude-sonnet-4-6 (again)        │
│  Receives tool results          │
│  Synthesises final response     │
│  stop_reason == "end_turn"      │
└────────────────┬────────────────┘
                 │ block.text (markdown)
                 ▼
┌─────────────────────────────────┐
│       Streamlit App Layer       │
│  - Clears status indicator      │
│  - Renders response in chat     │
│  - Appends to session history   │
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│         User (Browser)          │
│  Reads response, asks follow-up │
└─────────────────────────────────┘
```

---

## Section 4 — Agent Configuration Sheet

### 4a. Model Parameters

| Parameter | Value | Rationale |
|---|---|---|
| Model | claude-sonnet-4-6 (Anthropic) | Strong tool use performance; cost-efficient vs Opus for travel advisory tasks |
| Temperature | Default (1.0) | Travel advice benefits from natural, varied phrasing; lower temperature not needed for factual tool-grounded responses |
| Max tokens | 1000 | Sufficient for single-destination responses; may truncate complex multi-tool answers — monitor in evals |
| Timeout | Not set explicitly | Streamlit blocks on the API call; consider adding a 30s timeout in production |
| Top-p | Default | Temperature is the primary control here |
| Frequency penalty | Not set | Tool-use responses are naturally varied; no repetition problem observed |

> **When to change temperature:** Lower to 0.3–0.5 if outputs become too creative or inconsistent (e.g. inventing attractions). Raise toward 1.2+ only if responses feel robotic and formulaic across similar queries.

### 4b. Prompt Architecture

**System Prompt Role:** Establishes the agent's identity and instructs it to use tools for accurate answers rather than relying on training data alone.

```
You are a travel assistant. Use tools to give accurate, specific answers.
```

**User Prompt Role:** Passes the user's raw natural language query directly — no preprocessing or structured extraction.

```
{user_query}
```

Example: `"I want to visit Lisbon in November. Best time and what to do?"`

**Critical constraint:** The system prompt must explicitly instruct tool use ("Use tools") — without this, Claude may answer from training data and skip the ReAct loop entirely, producing ungrounded responses that bypass the tools.

### 4c. Memory Configuration

| Memory Type | Used? | Notes |
|---|---|---|
| In-context (conversation history) | Yes | `st.session_state.messages` accumulates all turns; passed to Claude each call |
| Vector / RAG | No | No unstructured knowledge base needed for v1 tool-grounded responses |
| External DB | No | No persistence across sessions; each page reload starts fresh |
| Session state | Yes | Streamlit `session_state` holds message history for the duration of the browser session |

**Upgrade path:** Adding a user profile store (preferred travel style, past destinations, budget tier) would allow personalised recommendations across sessions — highest value add for a returning user experience.

### 4d. Tools Configuration

| Tool | Used? | Notes |
|---|---|---|
| `get_weather` | Yes | Returns hardcoded weather string; replace with OpenWeatherMap API for real data |
| `search_attractions` | Yes | Returns hardcoded top-5 list; replace with Google Places API for real and ranked results |
| `estimate_budget` | Yes | Returns fixed INR figure per travel style; replace with live currency + cost-of-living API for accuracy |
| Web search | No | Not in scope for v1; would enable real-time event and travel advisory lookup |
| Calendar / booking | No | Out of scope — agent is advisory only, not transactional |

**Upgrade path:** The highest-value single tool addition is replacing `get_weather` with a real weather API (OpenWeatherMap free tier) — it's the tool users are most likely to act on directly.

---

## Section 5 — Data Flow & Security Notes

- **API key:** `ANTHROPIC_API_KEY` is read via `anthropic.Anthropic()` which looks for the env variable. If the key is hardcoded in the script or present in terminal history, it is at risk. Store in a `.env` file and never commit it.
- **User data sent externally:** The user's raw query text is sent to Anthropic's API on every turn. No PII is collected or inferred, but open-ended queries could contain personal information (e.g. "I'm travelling for my honeymoon to Paris").
- **Written to disk:** Nothing. Streamlit session state is in-memory only; no files are written.
- **Third-party data retention:** Anthropic may log API requests per their data retention policy. Review Anthropic's API data usage policy before deploying in a context where user queries are sensitive.
- **Tool outputs:** All tool outputs are simulated strings; no external API calls are made in v1.

---

## Section 6 — Data Grounding & Freshness

| Dimension | Detail |
|---|---|
| Data source | Simulated tool functions (hardcoded) + Claude claude-sonnet-4-6 training data for synthesis and formatting |
| Knowledge cutoff | Claude claude-sonnet-4-6 has a training cutoff — destination information (closures, new attractions, political situations) may be stale |
| Grounding method | None — no RAG, no web search, no live database |
| Freshness risk | High — weather strings, attraction lists, and budget figures are hardcoded and will never update |
| Mitigation | Display a clear UI disclaimer: "Outputs are simulated for demonstration purposes. Verify before booking." |
| Upgrade path | Replace all three tool functions with real API integrations; add a web search tool for real-time travel advisories |

---

## Section 7 — Eval Success Definition (Pre-Build)

> Written before scoring. Full results filled in Phase 4 Eval Scorecard.

| Criterion | What "good" looks like |
|---|---|
| Tool selection accuracy | The correct tool(s) are called for the query — weather queries trigger `get_weather`, budget queries trigger `estimate_budget`, etc. |
| Response completeness | All relevant tools are called; the response answers every implied sub-question in the user's query |
| Format quality | Response uses markdown headers, tables, or bullets where appropriate; not a wall of text |
| Synthesis quality | Tool outputs are woven into a coherent narrative, not just listed verbatim |
| Multi-turn coherence | Follow-up questions ("what about the budget?") are answered correctly using prior context |
| Edge case handling | Vague or incomplete queries produce a clarifying response or a reasonable best-effort answer, not a crash or empty response |

**Minimum bar for v1:** Tool calls fire correctly for at least 3 of the 5 test cases, and every response includes a readable, non-truncated answer. A response that skips all tools or produces raw JSON is a failing output.

---

## Section 8 — Excalidraw Diagram Notes

**Colour coding:**
- Blue boxes: User action / input points
- Green boxes: Anthropic API / Claude processing
- Orange boxes: Tool execution layer
- Purple boxes: Streamlit rendering / output

**Arrow labels:**
- User → Streamlit: "Natural language query"
- Streamlit → Claude: "messages[] + tools[]"
- Claude → Tool Dispatcher: "tool_use block"
- Tool Dispatcher → Tools: "function call + inputs"
- Tools → Tool Dispatcher: "result string"
- Tool Dispatcher → Claude: "tool_result in messages[]"
- Claude → Streamlit: "text block (markdown)"
- Streamlit → User: "Rendered chat message"

**Groupings:**
- Group Claude + Tool Dispatcher + Tools together as "Agent Core" — this is the ReAct loop
- Group Streamlit + User together as "UI Layer"
- Draw the ReAct loop as a cycle (Claude → Tools → Claude) with an exit arrow when `stop_reason == "end_turn"`

**Special annotations:**
- Mark the `stop_reason` check as the "loop exit condition" — this is where the agent decides it has enough information
- Mark `max_tokens=1000` as a constraint on the Claude output box — "truncation risk here"
- Mark the tool functions as "simulated — replace with real APIs in v2"
