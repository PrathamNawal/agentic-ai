# Design Document — Parallel Research Agent
> Phase 2: Design | Project: research-agent

---

## Section 1 — Agent Architecture Classification

| Dimension | This Agent | Why |
|---|---|---|
| Pattern | Prompt chain (parallel fan-out / fan-in) | Three independent analyst calls run concurrently, then feed a single synthesis call — no dynamic routing or loops |
| Memory | None | Each run is fully stateless; the topic is the only context needed |
| Tools | None (v1) | All knowledge comes from LLM training data; no external APIs called beyond Anthropic |
| Autonomy level | Level 2 — Prompt chain | Sequential (but parallelised) structured flow; the LLM never chooses the next step |
| Upgrade path | Level 3 — Add `web_search` tool to each analyst call for real-time grounding |

---

## Section 2 — Architecture Decision

| Level | Pattern | Description | This agent? |
|---|---|---|---|
| 1 | Single LLM call | One prompt in, one response out | ❌ |
| 2 | Prompt chain | Sequential calls, output feeds next | ✅ |
| 3 | ReAct loop | LLM reasons, picks tool, observes, repeats | ❌ |
| 4 | Multi-agent | Orchestrator delegates to specialists | ❌ |

**Decision rationale:**
- **Why Level 2 is right:** The research task has a fixed, known structure — always 3 angles, always synthesised. No dynamic branching is needed. Parallelism within a prompt chain gives the speed benefit of concurrent execution without the complexity of a ReAct loop.
- **What would require going higher:** If the agent needed to decide *which* research angles were relevant to a topic, or if it needed to search the web and incorporate live results, Level 3 (ReAct with tools) would be appropriate.
- **What complexity this avoids:** No tool selection logic, no loop termination condition, no partial result handling mid-loop — the fan-out/fan-in is structurally deterministic once triggered.

---

## Section 3 — Workflow Diagram

```
┌─────────────────────────────────────┐
│           USER INPUT                │
│      topic: string                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     research_agent(topic)           │
│     — orchestrator function         │
└──────┬────────────┬────────┬────────┘
       │            │        │
       ▼            ▼        ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ research │ │ research │ │ research │
│ _topic() │ │ _topic() │ │ _topic() │
│ angle:   │ │ angle:   │ │ angle:   │
│ market   │ │ risk     │ │ tech     │
└────┬─────┘ └────┬─────┘ └────┬─────┘
     │             │             │
     │   asyncio.gather()        │
     │   (all 3 in parallel)     │
     └──────────┬────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│     Exception filter                │
│     clean = [r for r in results     │
│       if not isinstance(r,Exception)│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     synthesize(topic, clean)        │
│     — combine 3 angle outputs       │
│     — single synthesis call         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     FINAL OUTPUT                    │
│     3-paragraph synthesis string    │
└─────────────────────────────────────┘
```

---

## Section 4 — Agent Configuration Sheet

### 4a. Model Parameters

| Parameter | Value | Rationale |
|---|---|---|
| Model | claude-sonnet-4-5 (Anthropic) | Balanced speed and quality for structured insight generation; Haiku would be faster/cheaper but risks generic outputs on niche topics |
| Temperature | Default (~1.0) | Not explicitly set in v1; slightly creative output is acceptable for brainstorming-style research |
| Max tokens (research) | 300 | Sufficient for 3 numbered insights; keeps cost and latency low per call |
| Max tokens (synthesis) | 500 | Allows a 3-paragraph summary; ~150–170 words, which is tight but achievable |
| Timeout | None set (v1) | No timeout guard — API default applies; risk of hanging on slow responses |
| Top-p | Default | Temperature is the primary randomness control for this use case |

> **When to change temperature:** Lower to 0.3–0.5 if outputs are too creative or inconsistent across runs on the same topic. Raise to 1.2+ only if outputs feel repetitive across angles (rare for 3 distinct personas).

### 4b. Prompt Architecture

**Research System Prompt Role:** Establishes a specific analyst persona to steer perspective and constrain output style.
```
You are a {angle} analyst. Be concise and specific.
```

**Research User Prompt Role:** Requests exactly 3 numbered insights to enforce parseable, scannable output.
```
Give 3 key insights about: {topic}. Use a numbered list.
```

**Synthesis System Prompt Role:** Instructs the model to act as an integrator, not as a fourth analyst.
```
Synthesize multi-perspective research into a coherent summary.
```

**Synthesis User Prompt Role:** Provides all three angle outputs and specifies output structure.
```
Topic: {topic}

Research from multiple angles:
{combined_angle_outputs}

Synthesize into a 3-paragraph summary.
```

**Critical constraint:** The research prompt requires a numbered list format — if the model ignores this, the synthesis prompt receives unstructured text, which still works but reduces output consistency.

### 4c. Memory Configuration

| Memory Type | Used? | Notes |
|---|---|---|
| In-context (conversation history) | No | Each call is a single-turn — no prior messages |
| Vector / RAG | No | All knowledge from LLM weights only |
| External DB | No | No persistence of runs or outputs |
| Session state | No | No state between `research_agent()` calls |

**Upgrade path:** Adding session memory (e.g. storing past topics + summaries in a list) would allow the agent to reference "last week you researched X — here's what's changed". High value for repeated users.

### 4d. Tools Configuration

| Tool | Used? | Notes |
|---|---|---|
| Web search | No | Highest-priority v2 addition — would ground all outputs in current sources |
| File output (save to .md) | No | Useful for PM users who want to save research — trivial to add |
| Slack/email notification | No | Useful for async workflows — not needed for v1 |

**Upgrade path:** Adding `web_search` to each analyst call is the single highest-value upgrade — it directly fixes the freshness risk (High) identified in the brief.

---

## Section 5 — Data Flow & Security Notes

- **API key:** Currently loaded from environment variable `ANTHROPIC_API_KEY`. If hardcoded in a notebook and pushed to GitHub, the key will be exposed. Always use `os.environ.get()` and add the notebook to `.gitignore`.
- **User data sent externally:** The `topic` string is sent to the Anthropic API in each prompt. Topics containing company-confidential information or personal data should be sanitised before use.
- **Disk writes:** None in v1 — output is printed to stdout only. No files are created.
- **Third-party retention:** Anthropic may log API inputs/outputs for safety monitoring per their usage policy. Do not use for topics containing PII or regulated data.

---

## Section 6 — Data Grounding & Freshness

| Dimension | Detail |
|---|---|
| Data source | Claude Sonnet training data (LLM weights only) |
| Knowledge cutoff | ~early 2025; topics post-cutoff will produce plausible-sounding but unverified insights |
| Grounding method | None — no RAG, no web search, no database lookup |
| Freshness risk | **High** — the agent is designed for fast-moving domains (AI, market trends, enterprise tech) where the most valuable insights are the most recent |
| Mitigation | Append a disclaimer to all outputs: *"Insights based on model training data; verify time-sensitive claims independently."* Do not use for topics where recency is critical (funding rounds, regulatory changes, product launches). |
| Upgrade path | Add Anthropic's `web_search_20250305` tool to each `research_topic` call — each analyst can then retrieve and cite live sources before generating insights |

---

## Section 7 — Eval Success Definition (Pre-Build)

> Written before scoring. Full results tracked in EVAL_SCORECARD.md.

| Criterion | What "good" looks like |
|---|---|
| Angle coverage | All 3 angles (market, risk, technology) are meaningfully represented in the synthesis — not just mentioned |
| Insight specificity | Research insights name concrete entities, numbers, or mechanisms — not generic statements like "there are risks" |
| Synthesis integration | The 3-paragraph summary weaves angles together rather than restating each in sequence |
| Format compliance | Research calls return numbered lists; synthesis returns exactly 3 paragraphs |
| Latency | End-to-end wall clock time ≤ 10 seconds for a mid-length topic |
| Error resilience | If one angle call fails, synthesis still completes on the remaining 2 angles with a logged warning |

**Minimum bar for v1:** The agent must complete synthesis from at least 2 of 3 angles within 15 seconds and produce a readable 3-paragraph output without crashing.

---

## Section 8 — Excalidraw Diagram Notes

**Colour coding:**
- 🟦 Blue boxes: User input and final output
- 🟨 Yellow boxes: Orchestrator / routing logic (`research_agent`, `asyncio.gather`, exception filter)
- 🟩 Green boxes: Analyst LLM calls (`research_topic` × 3) — these are the parallel workers
- 🟧 Orange box: Synthesis LLM call — the fan-in bottleneck

**Arrow labels:**
- Input → Orchestrator: `topic: str`
- Orchestrator → each analyst: `(topic, angle)` tuple
- Each analyst → gather: `{angle, insights}` dict
- gather → filter: `results list (may include Exceptions)`
- filter → synthesis: `clean results list`
- synthesis → output: `summary: str`

**Grouping:**
- Group the 3 analyst boxes together with a dashed border labelled "Parallel execution"
- Group orchestrator + filter into a "Coordination layer"

**Special annotation:**
- Mark the `asyncio.gather()` step as: ⚡ "This is where parallelism happens — all 3 start simultaneously"
- Mark the exception filter as: ⚠️ "Silent failure risk — user may not notice fewer than 3 angles"
