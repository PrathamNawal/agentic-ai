# ✈️ Travel Planning Agent — Agentic AI Design Patterns

A fully documented AI travel assistant built to demonstrate **Level 3 ReAct agentic patterns** using the Anthropic Claude API. The agent reasons about user intent, selects the right tools, and synthesises a complete travel response — all from a single natural language question.

This project ships with the complete **5-phase agentic AI lifecycle** documented end-to-end: from brief to design to evaluation to operations.

---

## What This Agent Does

Ask it anything about travel — and it figures out what to look up on your behalf.

> *"Plan a 5-day mid-range trip to Bangkok"*
> *"What's Lisbon like in November?"*
> *"What is Kyoto famous for?"*

The agent decides which tools to call, in what order, based on your question. It then synthesises the results into a single, readable response — with live tool call visibility while it works.

**Three tools available to the agent:**

| Tool | What it does |
|---|---|
| 🌤️ Get Weather | Returns climate conditions and best travel months for a destination |
| 🗺️ Search Attractions | Finds top tourist attractions in a city |
| 💰 Estimate Budget | Provides a daily travel budget estimate in INR by travel style |

---

## Why This Project Exists

This is not just a travel chatbot. It is a **learning project** designed to make the following concrete:

- What a **ReAct loop** looks like in practice — the LLM decides *which tools to call* dynamically, with no hardcoded routing
- Why **tool use changes the architecture** — this is a Level 3 agent, not a prompt chain
- How to apply a **full agentic lifecycle** to even a small project — brief → design → eval → ops
- What the real **engineering gaps** are between a demo and a production agent

---

## Architecture at a Glance

This agent operates at **Autonomy Level 3 — ReAct Loop**.

```
User Query  →  Claude reasons: which tools do I need?
            →  Tools fire (weather / attractions / budget)
            →  Claude synthesises all results
            →  Response rendered in Streamlit chat
```

The loop repeats until Claude decides it has enough information to answer — there is no hardcoded flow.

| Dimension | Detail |
|---|---|
| **Pattern** | ReAct loop — LLM-driven tool selection |
| **Model** | Claude Sonnet (Anthropic) |
| **Memory** | In-context, session-scoped |
| **Interface** | Streamlit chat UI |
| **Tools** | 3 simulated tool functions |
| **Autonomy level** | Level 3 of 4 |

---

## How to Run

**Prerequisites:** Python 3.9+, an Anthropic API key, and Streamlit installed.

Set your API key as an environment variable, then launch the app. The chat interface opens at `localhost:8501`.

Type your travel question in the input box at the bottom. Tool calls appear live as the agent works. The full response is rendered in the chat thread, and conversation history persists for follow-up questions within the session.

---

## Project Structure

```
travel-agent/
│
├── travel_agent_streamlit.py   ← Main Streamlit app
├── travel agent with tool use.py   ← Original CLI version
├── travel_agent_flask.py       ← Flask API version
├── travel_agent_api.py         ← FastAPI version
│
├── brief/
│   └── AGENT_BRIEF.md          ← Phase 1: Problem, persona, I/O spec
│
├── design/
│   └── DESIGN_DOC.md           ← Phase 2: Architecture, config, workflow
│
├── evals/
│   └── EVAL_SCORECARD.md       ← Phase 2 stub + Phase 4 scoring
│
└── ops/
    └── OPS_RUNBOOK.md          ← Phase 5: Security, cost, observability
```

---

## The 5-Phase Agentic Lifecycle

Every artifact in this project maps to a phase in the agentic AI development lifecycle. This is the opinionated framework used to build and document the agent.

### Phase 1 — Define › [`brief/AGENT_BRIEF.md`](brief/AGENT_BRIEF.md)

Defines the problem before any code is written.

- Who is the user and what is their pain?
- What does the agent take as input and produce as output?
- When should this agent *not* be used?
- What are the top 3 risks?

**Key insight from this agent's brief:** The core problem is not "travel information is hard to find" — it's that synthesising across multiple sources into a single, confident recommendation takes too long. The agent solves the synthesis step, not the search step.

---

### Phase 2 — Design › [`design/DESIGN_DOC.md`](design/DESIGN_DOC.md)

Translates the brief into an architecture decision — before any code.

- Why **Level 3 (ReAct loop)** and not a simpler prompt chain?
- What model parameters were chosen and why?
- What does the full data flow look like from query to response?
- What does "good output" look like — defined before building?

**Architecture decision:** A prompt chain (Level 2) would require hardcoding logic like "if the query mentions cost, call estimate_budget." The ReAct loop lets Claude decide — making the agent robust to query variation without brittle conditional logic.

---

### Phase 3 — Build

The code. Three interface versions were built from the same agent core:

| Version | When to use |
|---|---|
| **Streamlit** | Interactive chat UI — best for exploration and demos |
| **FastAPI** | REST API — best for integration with other services |
| **Flask** | Lightweight API — best for simplicity |

---

### Phase 4 — Evaluate › [`evals/EVAL_SCORECARD.md`](evals/EVAL_SCORECARD.md)

A structured scorecard with 5 test cases and a 100-point rubric — defined in Phase 2, scored after building.

**5 test cases:**

| ID | Query | What it tests |
|---|---|---|
| TC-01 | "I want to visit Lisbon in November. Best time and what to do?" | Happy path — weather + attractions |
| TC-02 | "What's in Tokyo?" | Edge case — minimal input, no month or style |
| TC-03 | "Plan a complete 7-day luxury trip to Bali in August" | Complex — all three tools, explicit style |
| TC-04 | "Is Ulaanbaatar worth visiting in January?" | Niche destination, harsh climate |
| TC-05 | "What will a 5-day mid-range Bangkok trip cost?" | Budget-only query |

**Scoring categories:** Tool selection accuracy (30pts) · Response quality & synthesis (40pts) · Format compliance (20pts) · Edge case handling (10pts)

**Predicted top failure:** TC-04 — the simulated `get_weather` tool returns "22-28°C, sunny" for Ulaanbaatar in January. In reality, Ulaanbaatar is the coldest capital city on earth in winter. This is the most credibility-damaging output in v1.

---

### Phase 5 — Operate › [`ops/OPS_RUNBOOK.md`](ops/OPS_RUNBOOK.md)

Everything needed to run, maintain, and evolve the agent safely.

**Security checklist highlights:**
- API key must be set as an environment variable — never hardcoded
- Add `.env` to `.gitignore` before first commit
- Set a monthly spend cap in the Anthropic Console
- The Streamlit app runs locally by default — review before any public deployment

**Cost at current pricing:** Approximately $0.005 per query on Claude Sonnet. At 1,000 queries, total cost is around $5.00.

**Prompt injection risk: Low** — tool functions are hardcoded with no shell access or database writes. A crafted query can confuse tool selection but cannot exfiltrate data or execute arbitrary code.

---

## Upgrade Roadmap

The agent pattern is right. The tools are the gap. In priority order:

| Upgrade | What it fixes | Complexity |
|---|---|---|
| Replace `get_weather` with OpenWeatherMap API | TC-04 credibility failure; identical weather for all cities | Low |
| Replace `search_attractions` with Google Places API | Generic, city-agnostic attraction list | Medium |
| Add `max_tokens` truncation detection in the UI | Silent response cut-off in complex queries | Low |
| Add API key validation at startup | Confusing crash on missing key | Low |
| Cap session history to last 10 turns | Unbounded token growth in long conversations | Low |
| Replace `estimate_budget` with live FX + cost-of-living API | Static INR figures regardless of city | Medium |

---

## Key Learning Objectives

This project was built to make specific agentic AI concepts concrete:

- **ReAct loop in practice:** The LLM selects tools dynamically — no routing logic in the application code. This is fundamentally different from a prompt chain.
- **`max_tokens` is a real constraint:** At 1,000 tokens, complex multi-tool synthesis responses get truncated. Tuning this parameter has direct UX consequences.
- **The tools are not the agent:** The intelligence is in Claude's reasoning about *which* tools to call and in *what order*. The tools themselves are simple functions.
- **Simulated tools reveal pattern, not value:** A demo with simulated data proves the architecture works. Real value requires replacing simulated functions with live APIs.

> **Key insight:** Replacing a simulated tool with a real API is where a demo agent becomes a production agent — and where the engineering complexity begins.

---

## What's Missing (Intentionally)

These are **not** in scope for v1 — and that's a deliberate choice, not an oversight:

- ❌ Real-time flight or hotel prices — this is an advisory agent, not a booking tool
- ❌ Cross-session memory — conversation resets on page reload by design
- ❌ Multilingual support — English-only queries in v1
- ❌ Concurrent user support — Streamlit's single-threaded model is not designed for production traffic

*This project demonstrates a complete agentic AI lifecycle, from problem definition to production operations, applied to a single focused agent. The goal is depth over breadth: one well-documented agent beats ten undocumented ones.*
