# Agent Brief — Parallel Research Agent
> Phase 1: Define | Project: research-agent

---

## Section 1 — Problem Statement

Researchers, PMs, and analysts need multi-perspective insight on a topic quickly, but manually consulting different analytical lenses (market, risk, technology) requires searching across sources, synthesising mentally, and often takes 30–60 minutes per topic. The current workaround is either a shallow single-angle search or a slow manual process stitching together separate research sessions.

**This agent solves:** Given any research topic, it delivers a 3-paragraph synthesised brief covering market opportunity, risk, and technology angles — in under 10 seconds — by running all three in parallel.

---

## Section 2 — User Persona

| Field | Detail |
|---|---|
| Name | Strategy Researcher / PM |
| Who | Product manager, analyst, or founder working in a fast-moving domain (e.g. AI, enterprise tech) |
| Context | Preparing for a meeting, writing a strategy doc, or quickly getting up to speed on an unfamiliar topic |
| Tech comfort | Intermediate — comfortable running a Python script or Jupyter notebook, not a software engineer |
| Goal | Get a balanced, multi-angle research brief in seconds, without opening 10 tabs |
| Frustration | Shallow single-perspective summaries, or spending too long manually aggregating views before they can start writing |

---

## Section 2a — Job-to-be-Done

> **When I** need to quickly understand a complex topic from multiple angles, **I want to** get parallel expert perspectives synthesised into one coherent brief, **so I can** start writing, deciding, or presenting without a long research detour.

---

## Section 3 — Input / Output Specification

**Inputs:**

| Input | Type | Example | Required |
|---|---|---|---|
| topic | string | "generative AI in Indian enterprises" | Yes |

**Outputs:**

| Output | Format | Description |
|---|---|---|
| Synthesised research brief | Plain text, 3 paragraphs | Covers market opportunity, risk/challenges, and technology/innovation angles in an integrated narrative |
| Per-angle insights (intermediate) | Dict with angle + numbered insights | 3 key insights per angle, used as input to synthesis |

---

## Section 4 — Step-by-Step Workflow

1. User provides a research topic as a string input to `research_agent(topic)`.
2. Agent fans out three parallel API calls — one each to a "market opportunity", "risk and challenge", and "technology and innovation" analyst persona.
3. Each analyst call receives the same topic and returns 3 numbered insights from its specific angle.
4. All three calls run concurrently via `asyncio.gather` — no call waits for another.
5. Agent collects completed results and filters out any failed calls (exception handling).
6. Agent reports how many of 3 perspectives succeeded.
7. Agent builds a combined prompt from all successful angle outputs.
8. Agent sends the combined research to a synthesis call that integrates the angles into a 3-paragraph summary.
9. Agent returns the final synthesised brief as a string.
10. User reads the output — ready to use in a doc, presentation, or meeting.

---

## Section 5 — Success Metrics

| Metric | Target | How to Measure |
|---|---|---|
| End-to-end latency | < 10 seconds for 3 perspectives + synthesis | `time.time()` wrapper around full `research_agent()` call |
| Parallel efficiency | All 3 research calls complete within 1s of each other | Compare individual call durations |
| Synthesis coherence | 3 paragraphs that integrate all three angles without repetition | Manual review or LLM-as-judge rubric |
| Insight specificity | Each angle produces 3 numbered, non-generic insights | Manual spot-check: does "risk" name actual risks, not platitudes? |
| Error resilience | Agent completes synthesis even if 1 of 3 calls fails | Run with intentional failure on one angle |

---

## Section 6 — Constraints & Assumptions

**Constraints:**
- Requires a valid `ANTHROPIC_API_KEY` set in the environment before running
- Max tokens capped at 300 per research call and 500 for synthesis — limits depth
- No persistent memory — each run is stateless; prior research is not recalled
- No real-time data — LLM knowledge cutoff applies; cannot surface last-week news
- Output is text only — no citations, links, or source verification
- Must run in an environment supporting Python `asyncio` (Jupyter or `.py` script)

**Assumptions:**
- The topic is a coherent English-language phrase, not a raw URL or code snippet
- The user wants breadth-first coverage, not deep-dive specialist research
- Three perspectives (market, risk, technology) are sufficient for the target use case
- The Anthropic API is accessible and responsive (no network proxy issues)
- The user will apply their own judgment before acting on the output

---

## Section 7 — Contra-Indicators (When NOT to Use This Agent)

| Situation | Why it's unfit | Better alternative |
|---|---|---|
| Topic requires data from the last 30 days | LLM knowledge cutoff means recent events are missed | Use Perplexity, web search, or add a search tool |
| User needs cited sources for a report | Agent produces no citations or verifiable references | Use a RAG-based research tool or manual research |
| Topic is highly niche or technical (e.g. "RISC-V cache coherence protocols") | LLM training data is sparse; insights will be generic | Use specialist databases, arXiv, or domain experts |
| Compliance or legal research context | Output lacks sourcing and could be factually wrong | Use verified legal databases with human review |
| User needs more than 3 angles (e.g. geopolitical, regulatory, competitive) | Fixed 3-angle architecture — not configurable yet | Extend to N-angle version or use a dynamic orchestrator |
| User needs interactive Q&A on the research | Stateless — no memory between calls | Add conversation history or use a chat interface |

---

## Section 8 — Data Grounding & Freshness

| Dimension | Detail |
|---|---|
| Data source | Claude Sonnet LLM training data only |
| Knowledge cutoff | Anthropic training cutoff (~early 2025); topics post that date will produce hallucinated or absent insights |
| Grounding method | None — no RAG, no web search, no database |
| Freshness risk | **High** — the agent is often used for fast-moving domains (AI, markets) where the most valuable insights are recent |
| Mitigation | Add a disclaimer to outputs; user should cross-check time-sensitive claims; mark outputs as "as of model training" |
| Upgrade path | Add `web_search` tool to each analyst call so each angle is grounded in current sources |

---

## Section 9 — Top 3 Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM produces confident but stale or hallucinated insights on fast-moving topics | High | High — user acts on wrong information | Add output disclaimer; upgrade to web search grounding |
| One or more parallel calls fail silently, producing a synthesis on fewer than 3 angles without the user noticing | Medium | Medium — unbalanced synthesis passes as complete | Surface angle count prominently in output; consider hard-failing if < 2 angles succeed |
| Token budget (300 / 500) truncates insights, cutting off the most important point | Medium | Medium — synthesis is incomplete without user realising | Monitor for truncated outputs; increase max_tokens or add a check for truncation markers |

---

## Section 10 — Learning Objectives (PM Lens)

- **Prompt engineering concept:** Role-playing via system prompt — each analyst call uses a distinct persona to steer the LLM's perspective, a foundational prompting technique.
- **LLM parameter:** `max_tokens` — the agent makes the tradeoff between speed/cost and output completeness very concrete; students see what truncation looks like in practice.
- **Key architectural insight:** This is a **fan-out / fan-in prompt chain with parallelism**, not a true ReAct agent — there is no tool use, no dynamic routing, and no loop. The LLM never "decides" what to do next.
- **Natural next level upgrade:** Add a `web_search` tool to each research call, making each analyst grounded in real current sources — this moves the agent from Level 2 (prompt chain) to Level 3 (ReAct with tools).

> **Key insight for this project:** Parallelism with `asyncio.gather` is the single highest-leverage optimisation available in a prompt chain — it turns a 15-second sequential pipeline into a 5-second concurrent one with zero added complexity.
