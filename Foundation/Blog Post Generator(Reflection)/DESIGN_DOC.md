# Design Document — Blog Post Generator (Reflection Pattern)
> Phase 2: Design | Project: Blog Post Generator Agent
> Status: Complete

---

## Section 1 — Agent Architecture Classification

| Dimension | This Agent | Why |
|---|---|---|
| Pattern | Prompt chain (Level 2) | Three sequential LLM calls with outputs feeding the next; no branching, no tool use, no iterative loop |
| Memory | In-context only (within each call) | Each call receives all necessary context in its prompt; no cross-run memory needed for v1 |
| Tools | None | Content generation from LLM training data is sufficient for blog intros; web search is a v2 upgrade |
| Autonomy level | Level 2 — Prompt chain | Sequential calls, structured flow; orchestration logic is Python, not LLM-driven |
| Upgrade path | Level 3 — add a quality-scoring step; if score < threshold, loop back to revise (ReAct-style) |

---

## Section 2 — Architecture Decision

| Level | Pattern | Description | This agent? |
|---|---|---|---|
| 1 | Single LLM call | One prompt in, one response out | ❌ — one call can't produce draft + critique + revision |
| 2 | Prompt chain | Sequential calls, output feeds next | ✅ — three calls, each consuming the previous output |
| 3 | ReAct loop | LLM reasons, picks tool, observes, repeats | ❌ — no tool use; loop would require quality scoring |
| 4 | Multi-agent | Orchestrator delegates to specialists | ❌ — overkill; no parallel workstreams or specialist routing needed |

- **Why this level is right:** The task has three fixed, sequential sub-tasks (generate → critique → revise). The structure is deterministic and known in advance — no LLM decision-making about which step to run next is required.
- **What would require going higher:** If we added a quality loop ("keep revising until score ≥ 7/10"), the agent would need a scoring call and conditional branching → Level 3. If we added parallel generation of multiple draft styles, → Level 4.
- **What complexity this avoids:** No state management, no tool permission grants, no loop exit condition bugs, no LangGraph orchestration overhead — the Python control flow is 15 lines.

---

## Section 3 — Workflow Diagram

```
┌─────────────────────────────────────────┐
│           USER PROVIDES INPUTS           │
│    topic = "..."   audience = "..."      │
└───────────────────┬─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│         CALL 1 — PRODUCER               │
│  System: "You are a content writer      │
│           for {audience}"               │
│  User:   "Write 300-word intro about    │
│           {topic}"                      │
│  max_tokens: 600                        │
└───────────────────┬─────────────────────┘
                    │  draft
                    ▼
┌─────────────────────────────────────────┐
│         CALL 2 — CRITIC                 │
│  System: "You are a harsh content       │
│           editor. Be specific."         │
│  User:   "Review this for {audience}.   │
│           Evaluate: hook, clarity,      │
│           examples, actionability,      │
│           tone. Draft: {draft}"         │
│  max_tokens: 400                        │
└───────────────────┬─────────────────────┘
                    │  critique
                    ▼
┌─────────────────────────────────────────┐
│         CALL 3 — REVISER (Producer)     │
│  System: (none — defaults to helpful)   │
│  User:   "Rewrite this post using all   │
│           feedback. Original: {draft}   │
│           Feedback: {critique}"         │
│  max_tokens: 600                        │
└───────────────────┬─────────────────────┘
                    │  revised
                    ▼
┌─────────────────────────────────────────┐
│         TERMINAL OUTPUT                 │
│  === DRAFT ===                          │
│  === CRITIQUE ===                       │
│  === REVISED ===                        │
└─────────────────────────────────────────┘
```

---

## Section 4 — Agent Configuration Sheet

### 4a. Model Parameters

| Parameter | Value | Rationale |
|---|---|---|
| Model | claude-sonnet-4-5 (Anthropic) | Strong creative writing + structured critique; cost-effective vs Opus |
| Temperature (Producer) | Default (~1.0) | Creative content — needs variety and voice; determinism is counterproductive |
| Temperature (Critic) | Default (~1.0) | Critique quality is insensitive to temperature; no tuning needed in v1 |
| Max tokens (Producer) | 600 | ~450 words — enough for a 300-word intro with breathing room |
| Max tokens (Critic) | 400 | ~300 words of critique — enough to cover 5 dimensions without padding |
| Timeout | Not set (default SDK) | Notebook-local; no user-facing timeout risk in v1 |
| Top-p | Default | Temperature is the primary control; top-p is not needed |

> **When to change temperature:** Lower to 0.3–0.5 for the Critic call if you want more consistent, reproducible critique across multiple runs of the same draft. Keep Producer at default (or 0.8+) to avoid repetitive drafts on repeated topics.

### 4b. Prompt Architecture

**System Prompt (Call 1 — Producer):**
Anchors the writer persona and audience awareness.
```
You are a content writer for {audience}. Write clearly and concisely.
```

**User Prompt (Call 1 — Producer):**
Gives the specific task and scope constraint.
```
Write a 300-word blog post intro about: {topic}
```

**System Prompt (Call 2 — Critic):**
Establishes a harsh, objective evaluator identity — the key separation-of-concerns move.
```
You are a harsh but fair content editor. Be specific about what is weak.
```

**User Prompt (Call 2 — Critic):**
Provides the draft and a structured 5-dimension rubric so the critique is never vague.
```
Review this blog post for {audience}. Evaluate:
1. Opening hook strength (is it compelling?)
2. Clarity of the core message
3. Specific examples vs. vague claims
4. Actionability — does the reader know what to do?
5. Tone match for {audience}
Draft:
{draft}
List concrete improvements. Be specific.
```

**User Prompt (Call 3 — Reviser):**
Passes both artefacts and demands full incorporation, not cherry-picking.
```
Rewrite this post incorporating all the feedback:
Original:
{draft}
Feedback:
{critique}
Revised version:
```

**Critical constraint:** The critic prompt's numbered 5-dimension structure is non-negotiable — removing it causes the critique to collapse into generic feedback, which makes the revision step nearly useless.

### 4c. Memory Configuration

| Memory Type | Used? | Notes |
|---|---|---|
| In-context (conversation history) | No | Each call is independent; context is passed explicitly via prompt injection, not conversation turns |
| Vector / RAG | No | No retrieval in v1 |
| External DB | No | No persistence |
| Session state | Python variables only | `draft` and `critique` are held in-process between calls |

**Upgrade path:** Persisting `(topic, audience, draft, critique, revised)` tuples to a SQLite DB would enable a feedback loop — "what topics have I written about before? What critique patterns keep recurring?"

### 4d. Tools Configuration

| Tool | Used? | Notes |
|---|---|---|
| Web search | No | Not needed for concept-driven blog intros; would add latency and cost |
| File export | No | Prints to stdout only in v1; Markdown file export is a 2-line addition |
| Brand voice retrieval | No | No brand guidelines input in v1 |
| Quality scorer | No | Critique is qualitative only; a numeric score would enable looping |

**Upgrade path:** Adding a web_search tool to Call 1's context (inject recent articles on the topic) would be the highest-leverage single addition — it grounds the draft in current discourse rather than LLM training data.

---

## Section 5 — Data Flow & Security Notes

- **API key:** Currently set via `os.environ["ANTHROPIC_API_KEY"]` (comment in code). Risk: if the key is hardcoded in a notebook cell, it will appear in `.ipynb` output and commit history. Fix: use `python-dotenv` and add `.env` to `.gitignore`.
- **User data sent to Anthropic:** The `topic` and `audience` strings, plus all generated content, are sent to Anthropic's API. No PII in v1 (topic/audience are generic strings), but if a user provides personal details (e.g. "write about my company's product"), that content leaves the local machine.
- **Written to disk:** Nothing — all output is printed to console. No log files created.
- **Third-party retention:** Anthropic's API data retention policies apply. Review at anthropic.com/privacy for production use.

---

## Section 6 — Data Grounding & Freshness

| Dimension | Detail |
|---|---|
| Data source | LLM training data only (Claude Sonnet 4.5) |
| Knowledge cutoff | Training cutoff means the agent cannot reference events, studies, or trends after the cutoff date |
| Grounding method | None |
| Freshness risk | Medium — conceptual PM/AI topics age at 6–18 month cycles; specific stat references would be unreliable |
| Mitigation | User should verify any statistics, product names, or industry references in the revised output before publishing |
| Upgrade path | Inject web_search results on the topic into the Producer prompt before drafting; this is the single highest-freshness improvement for v2 |

---

## Section 7 — Eval Success Definition (Pre-Build)

> Written before code runs. Full scoring happens in Phase 4 Eval Scorecard.

| Criterion | What "good" looks like |
|---|---|
| Hook quality | Opening sentence raises a specific tension, question, or contrarian claim — not a generic "AI is changing X" opener |
| Critique coverage | All 5 rubric dimensions (hook, clarity, examples, actionability, tone) addressed with at least one concrete suggestion each |
| Revision improvement | Revised draft addresses ≥ 3 of the critique's specific suggestions; verifiable by cross-referencing critique and revised text |
| Audience tone match | A blind reader familiar with Indian tech PM culture would identify the target audience correctly without being told |
| Format compliance | Draft and revised are 250–350 words; critique is 150–300 words with numbered points |

**Minimum bar for v1:** The revised draft must be meaningfully different from the draft (not just synonym substitution), and the critique must name at least 3 specific, actionable improvements.

---

## Section 8 — Excalidraw Diagram Notes

**Colour coding:**
- 🟦 Blue boxes: User inputs (topic, audience)
- 🟩 Green boxes: LLM calls (Producer Call 1, Critic Call 2, Reviser Call 3)
- 🟨 Yellow boxes: Intermediate artefacts (draft, critique)
- 🟥 Red box: Final output (revised)
- ⬜ White annotations: system prompt content on each LLM box

**Arrow labels:**
- Input → Call 1: "topic + audience"
- Call 1 → draft: "generate_post()"
- draft → Call 2: "critique_post(draft, audience)"
- Call 2 → critique: "structured 5-point critique"
- draft + critique → Call 3: "revise_post(draft, critique)"
- Call 3 → revised: "revised post"

**Grouping:**
- Group Call 1 + Call 3 together as "Producer" with a dashed border
- Call 2 stands alone as "Critic"
- Add annotation on the Critic box: "KEY: separate system prompt = objective critique"

**Special annotations:**
- Mark the gap between Call 1 and Call 3 as "This is the critical path — if critique is vague here, the revision fails"
- Mark max_tokens on each LLM box as a constraint label
