# Agent Brief — Blog Post Generator (Reflection Pattern)
> Phase 1: Define | Project: Blog Post Generator Agent
> Status: Complete

---

## Section 1 — Problem Statement

Content writers and PMs drafting blog posts often produce generic first drafts that lack a compelling hook, concrete examples, or the right tone for their audience. Without structured critique, revision is guesswork — the writer doesn't know *what* is weak, only that it is. Manual editing cycles are slow and depend on finding a skilled human reviewer.

**This agent solves:** A PM provides a topic and target audience, and receives a revised, audience-tuned blog post intro in under 30 seconds — with a structured critique explaining every improvement made.

---

## Section 2 — User Persona

| Field | Detail |
|---|---|
| Name | Solo Content PM |
| Who | Product Manager or solo founder at an Indian tech company, writing thought leadership content for LinkedIn, company blog, or product newsletters |
| Context | Has a topic in mind but limited time; needs a polished first draft without hiring a copywriter |
| Tech comfort | Moderate — comfortable running a Python script or Jupyter notebook, not a developer |
| Goal | Get a publication-ready 300-word blog intro that sounds like them, tuned to their audience |
| Frustration | First drafts are either too generic ("AI is transforming X...") or too technical for the intended reader |

---

## Section 2a — Job-to-be-Done (JTBD)

> **When I** have a topic I want to write about but no time to draft and self-edit, **I want to** get a critique-informed revision automatically, **so I can** publish content that actually resonates with senior PMs without spending hours iterating.

---

## Section 3 — Input / Output Specification

**Inputs:**

| Input | Type | Example | Required |
|---|---|---|---|
| topic | string | "why product managers need to understand AI agents" | Yes |
| audience | string | "senior product managers at Indian tech companies" | Yes |

**Outputs:**

| Output | Format | Description |
|---|---|---|
| draft | Plain text | ~300-word first-pass blog intro, audience-aware |
| critique | Plain text | Structured feedback across 5 dimensions: hook, clarity, examples, actionability, tone |
| revised | Plain text | Rewritten intro incorporating all critique points |

---

## Section 4 — Step-by-Step Workflow (Plain English)

1. User provides a `topic` string and an `audience` string in the script.
2. Agent builds a system prompt instructing the writer persona to match the given audience's expectations.
3. Agent sends the first LLM call (Producer) to generate a 300-word blog post intro on the topic.
4. Agent receives the draft and stores it in memory for the next call.
5. Agent builds a second prompt with the draft embedded, instructing a harsh content editor persona to critique it against 5 specific criteria.
6. Agent sends the second LLM call (Critic) — **separate call, separate system prompt** — to generate structured critique.
7. Agent receives the critique and stores it.
8. Agent sends the third LLM call (Producer again), passing both the original draft and the critique, requesting a full rewrite.
9. Agent receives the revised post.
10. Agent prints all three artefacts: Draft → Critique → Revised.

---

## Section 5 — Success Metrics

| Metric | Target | How to Measure |
|---|---|---|
| End-to-end latency | < 30 seconds | Time from script start to final print |
| Critique specificity | All 5 dimensions addressed | Manual check: does critique mention hook, clarity, examples, actionability, tone? |
| Revision improvement | Revised scores higher on at least 3 of 5 dimensions | Human A/B rating of draft vs revised |
| Audience tone match | Reader correctly identifies target audience | Blind test: show revised to 3 people and ask who it's written for |
| Token cost per run | < $0.02 per run | Calculate from API usage logs |

---

## Section 6 — Constraints & Assumptions

**Constraints:**
- Requires a valid `ANTHROPIC_API_KEY` set as an environment variable
- Outputs are printed to console only — no file export in v1
- Single-pass reflection only — no iterative loop until quality threshold is met
- Max output is 600 tokens per LLM call; longer posts will be truncated
- No memory across runs — each execution starts fresh
- Designed for English-language content only in v1

**Assumptions:**
- User can set environment variables and run a Python script
- Topic and audience are provided as hard-coded strings (not user input at runtime)
- The Anthropic API is available and not rate-limited
- Claude Sonnet 4.5 is the right model — good quality at reasonable cost for this use case

---

## Section 7 — Contra-Indicators (When NOT to Use This Agent)

| Situation | Why it's unfit | Better alternative |
|---|---|---|
| Full article (1,500+ words) | Agent is configured for 300-word intros; longer content will be truncated or incoherent | Use a chained agent with section-by-section generation |
| Real-time audience data needed | Agent has no web access; can't incorporate latest trends or viral formats | Add web search tool to pull trending content before drafting |
| Brand voice must be strictly preserved | Agent has no memory of past posts or brand guidelines | Ground the prompt with brand voice examples before generating |
| Multiple content formats (email, LinkedIn, tweet thread) | Agent produces one format; repurposing requires redesign | Use a routing pattern to dispatch to format-specific agents |
| Non-English languages | System prompts and critic criteria are in English; quality degrades for other languages | Localise all system prompts and test critique dimensions per language |
| Regulatory or compliance-sensitive content | No fact-checking, legal review, or hallucination guard rails | Add retrieval grounding and a human-in-the-loop approval step |

---

## Section 8 — Data Grounding & Freshness

| Dimension | Detail |
|---|---|
| Data source | LLM training data only — no external grounding |
| Knowledge cutoff | Claude Sonnet 4.5 has a training cutoff; any industry trend or stat referenced in the blog may be outdated |
| Grounding method | None in v1 |
| Freshness risk | Medium — blog intros about conceptual topics (e.g. "why PMs need to understand AI") age slowly; posts referencing recent events or data would be unreliable |
| Mitigation | User should fact-check any specific claims or statistics in the revised draft before publishing |
| Upgrade path | Add web_search tool to inject current articles or stats into the producer prompt before drafting |

---

## Section 9 — Top 3 Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Critic produces vague feedback ("make it more engaging") rather than specific, actionable critique | Medium | High — revision can't improve on vague feedback, wasting all three LLM calls | Critic prompt explicitly requires numbered, concrete notes per dimension; add an output format requirement |
| Revised draft is a minor rewrite of the original, not a genuine improvement | Medium | Medium — user gets marginal value over a single LLM call | Instruct the reviser to explicitly address each critique point; add a check step that compares draft vs revised length and structure |
| API key exposed in script or Jupyter notebook output | High (for beginners) | High — financial exposure, account compromise | Move API key to `os.environ`; add `.gitignore` for notebooks; document in README |

---

## Section 10 — Learning Objectives (PM Lens)

- **Prompt engineering concept demonstrated:** Persona separation — using distinct system prompts per role (writer vs. critic) yields more objective critique than asking the same agent to self-review
- **LLM parameter made concrete:** `max_tokens` as a quality ceiling — set too low (400 for critique), structured feedback gets cut off; the tradeoff between cost and completeness is visible here
- **Key architectural insight:** This is a **prompt chain, not a true agent** — there is no LLM-driven decision-making or tool use; the orchestration logic is entirely in Python, not in the model
- **Natural next level upgrade:** Add an iterative loop with a quality score threshold (e.g. run critique → if score < 7/10 → revise → repeat up to 3x), which turns this into a true ReAct-style agent

> **Key insight for this project:** Separating the producer and critic into distinct LLM calls with distinct system prompts is the single architectural decision that makes the reflection pattern actually work — the same model, given two different identities, produces meaningfully different and more honest evaluations.
