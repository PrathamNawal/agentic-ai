# Agent Brief — Travel Planning Agent
> Phase 1: Define | Project: Travel Agent with Tool Use

---

## Section 1 — Problem Statement

Travel planning requires stitching together information from multiple sources — weather sites, travel blogs, budget calculators — before a traveller can make a confident decision. Without this agent, a user must manually visit several tools, reconcile inconsistent information, and synthesise it themselves, a process that takes 20–40 minutes for even a simple query.

**This agent solves:** A traveller gets destination-specific weather, top attractions, and a daily budget estimate in a single conversational response, in under 30 seconds, via a Streamlit chat interface.

---

## Section 2 — User Persona

| Field | Detail |
|---|---|
| Name | Independent Traveller |
| Who | Individual planning a leisure or business trip; age 25–45; uses Google, travel blogs, and booking apps |
| Context | Early planning stage — deciding on a destination or preparing for an upcoming trip; does not yet have tickets booked |
| Tech comfort | Comfortable with apps and chat interfaces; not a developer; expects answers, not raw data |
| Goal | Get a quick, reliable snapshot of a destination without tabbing between five different sites |
| Frustration | Spends too long aggregating advice from multiple sources; gets generic or outdated information; can't quickly compare destinations |

---

## Section 2a — Job-to-be-Done (JTBD)

> **When I** am deciding where to travel or preparing for a trip, **I want to** ask a single question and get weather, things to do, and a realistic budget, **so I can** make a confident decision without spending an hour researching.

---

## Section 3 — Input / Output Specification

**Inputs:**

| Input | Type | Example | Required |
|---|---|---|---|
| Natural language query | String | "Plan a 5-day mid-range trip to Bangkok" | Yes |
| City (extracted by agent) | String | "Bangkok" | Yes (agent infers) |
| Month (extracted by agent) | String | "November" | No (agent infers from query) |
| Travel style (extracted by agent) | Enum: budget / mid-range / luxury | "mid-range" | No (agent infers or asks) |

**Outputs:**

| Output | Format | Description |
|---|---|---|
| Conversational response | Markdown text | Synthesised answer covering weather, attractions, and/or budget depending on the query |
| Tool call trace | Inline UI labels | Live display of which tools were called and with what inputs while the agent is working |
| Chat history | Session state | Full conversation retained for follow-up questions within the session |

---

## Section 4 — Step-by-Step Workflow (Plain English)

1. User opens the Streamlit app in a browser and sees a chat interface.
2. User types a travel question in the chat input box (e.g. "What's Lisbon like in November?").
3. The agent sends the user's message to Claude claude-sonnet-4-6 with a system prompt identifying it as a travel assistant with three available tools.
4. Claude decides which tools are needed to answer the question and in what order.
5. For each tool call, the app displays a live status message (e.g. "Calling `get_weather` with `{city: Lisbon, month: November}`").
6. Each tool executes and returns a result (weather conditions, attraction list, or budget figure).
7. The tool results are fed back to Claude as context.
8. Claude synthesises all tool results into a single, readable markdown response.
9. The response is displayed in the chat thread as the assistant's reply.
10. The conversation persists so the user can ask follow-up questions within the same session.

---

## Section 5 — Success Metrics

| Metric | Target | How to Measure |
|---|---|---|
| Response latency | < 15 seconds end-to-end | Timer from query submission to full response render |
| Tool call accuracy | Correct tool called for 90%+ of queries | Manual review of tool call log vs query intent |
| Response completeness | All relevant tools used for the query type | Check that weather + attractions + budget are each triggered when relevant |
| Format readability | Response uses headers and tables where appropriate | Manual review of 10 sample outputs |
| Follow-up coherence | Agent maintains context across 3+ turns correctly | Test multi-turn conversations manually |

---

## Section 6 — Constraints & Assumptions

**Constraints:**
- All three tools (`get_weather`, `search_attractions`, `estimate_budget`) are simulated — they return hardcoded responses, not real API data.
- Budget figures are fixed per travel style in INR; they do not vary by city.
- The agent has no persistent memory across sessions — conversation resets on page reload.
- No user authentication — anyone with access to the Streamlit URL can use the agent.
- `ANTHROPIC_API_KEY` must be set in the environment; the agent has no fallback.
- `max_tokens` is capped at 1000 — very long synthesis responses may be truncated.

**Assumptions:**
- Users will ask questions in English.
- Users have access to a browser and the Streamlit server is running locally or deployed.
- The simulated tool data is sufficient to demonstrate the agentic pattern — real data accuracy is not a v1 requirement.
- Claude correctly infers city, month, and travel style from natural language without explicit structured input.

---

## Section 7 — Contra-Indicators (When NOT to Use This Agent)

| Situation | Why it's unfit | Better alternative |
|---|---|---|
| User needs real-time flight or hotel prices | Tools are fully simulated — no live booking data | Kayak, Google Flights, or a real travel API integration |
| User needs visa or entry requirement information | LLM knowledge may be outdated; no grounding source | Official government travel advisory sites |
| User wants to book or transact | Agent is read-only and advisory only | Booking.com, Airbnb, or a transactional travel platform |
| Non-English queries | Agent is not prompted for multilingual support | Add a multilingual system prompt or use a translation layer |
| High-volume production deployment | Streamlit's single-threaded model doesn't support concurrent users well | Migrate to FastAPI + a proper frontend |
| Compliance-sensitive travel (corporate policy, sanctions) | No policy engine or compliance check is wired in | A rules-based compliance tool or HR travel system |

---

## Section 8 — Data Grounding & Freshness

| Dimension | Detail |
|---|---|
| Data source | Simulated tool functions (hardcoded strings); Claude training data for synthesis |
| Knowledge cutoff | Claude claude-sonnet-4-6 training data has a cutoff — real-world travel conditions post-cutoff are not reflected |
| Grounding method | None — no RAG, web search, or live database |
| Freshness risk | High — tool data is static; weather, prices, and attraction details will not reflect current conditions |
| Mitigation | Use this agent for pattern demonstration only; clearly label outputs as simulated in the UI |
| Upgrade path | Replace simulated tools with real APIs: OpenWeatherMap for weather, Google Places for attractions, a live FX/budget API for costs |

---

## Section 9 — Top 3 Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| User treats simulated outputs as real travel advice and makes decisions based on incorrect data | High | High | Add a prominent disclaimer in the UI: "Simulated data — for demonstration only" |
| `ANTHROPIC_API_KEY` is hardcoded or leaked via notebook/git history | Medium | High | Store key in environment variable; add `.env` to `.gitignore`; rotate key if exposed |
| `max_tokens=1000` causes response truncation for complex multi-tool queries | Medium | Medium | Increase `max_tokens` to 2000–4000; add a truncation warning in the UI if `stop_reason == "max_tokens"` |

---

## Section 10 — Learning Objectives (PM Lens)

- **Prompt engineering concept:** Tool use with a ReAct loop — the agent reasons about *which* tool to call before calling it, rather than executing a fixed sequence.
- **LLM parameter made concrete:** `max_tokens` directly limits how much the agent can synthesise; at 1000 tokens, long multi-tool responses risk cutoff.
- **Key architectural insight:** This is a true Level 3 ReAct agent — the LLM drives tool selection dynamically. It is not a prompt chain; the loop only terminates when Claude decides it has enough information to answer.
- **Natural upgrade:** Replace simulated tools with real API calls to make the agent production-useful; then add session memory to support multi-session travel planning.

> **Key insight for this project:** The agentic power here is not in the tools themselves — it's in Claude deciding *which* tools to call and in *what order* based on the user's intent, with no hardcoded routing logic.
