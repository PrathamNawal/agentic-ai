# 🖊️ Blog Post Generator Agent
### A Reflection Pattern Implementation using Claude AI

> **Write → Critique → Revise** — automated, audience-aware, and surprisingly honest about your drafts.

---

## What This Is

A lightweight AI agent that takes a **topic** and a **target audience** and produces a publication-ready blog post intro in three steps:

1. **Draft** — a first-pass intro written for your specific audience
2. **Critique** — a structured, no-fluff editorial review across 5 dimensions
3. **Revised** — a rewrite that actually incorporates the feedback

The key architectural move: the critic is a **separate LLM call with a separate persona**. Same model, different identity — which produces meaningfully more honest feedback than asking the same agent to self-review.

---

## The Reflection Pattern

This agent implements the **Producer–Critic** variant of the Reflection agentic design pattern.

```
User Input (topic + audience)
        │
        ▼
┌──────────────────┐
│  PRODUCER (Call 1) │  → First draft
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  CRITIC  (Call 2)  │  → 5-dimension critique
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  REVISER (Call 3)  │  → Improved final draft
└──────────────────┘
        │
        ▼
   Terminal Output
```

The orchestration logic lives entirely in Python — this is a **Level 2 Prompt Chain**, not a fully autonomous agent. The model doesn't decide what to do next; the code does. That's intentional. It keeps the system debuggable, predictable, and cheap to run.

---

## What "Reflection Pattern" Means Here

Most AI content tools run a single LLM call. You get what you get.

Reflection adds a structured feedback loop:

| Without Reflection | With Reflection |
|---|---|
| One-shot output, quality varies | Draft → critique → revision cycle |
| No visibility into what's weak | 5 explicit dimensions evaluated |
| Same agent reviews its own work | Separate critic persona = fresh eyes |
| You do the editing | Agent does the editing |

The tradeoff: **3× the API calls, ~3× the cost, meaningfully better output quality** for content where polish matters.

---

## Critique Dimensions

The Critic evaluates every draft against five specific criteria:

| # | Dimension | What It Checks |
|---|---|---|
| 1 | **Opening Hook** | Is the first sentence compelling, or does it open with "AI is transforming X"? |
| 2 | **Core Message Clarity** | Can a reader state the main point in one sentence after reading? |
| 3 | **Specificity** | Concrete examples vs. vague claims |
| 4 | **Actionability** | Does the reader know what to do or think differently after reading? |
| 5 | **Tone Match** | Does it actually sound right for the stated audience? |

---

## Quickstart

**Prerequisites:** Python 3.8+, an Anthropic API key

```bash
# 1. Clone the repo
git clone https://github.com/your-username/blog-post-generator-agent
cd blog-post-generator-agent

# 2. Install dependencies
pip install anthropic python-dotenv

# 3. Set your API key
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# 4. Edit topic and audience in the script, then run
python blog_agent.py
```

**Output:**
```
=== DRAFT ===
[~300-word first draft]

=== CRITIQUE ===
[Structured 5-point editorial feedback]

=== REVISED ===
[Improved version incorporating all critique]
```

---

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `topic` | `"why PMs need to understand AI agents"` | What to write about |
| `audience` | `"senior PMs at Indian tech companies"` | Who it's written for |
| `model` | `claude-sonnet-4-5` | LLM used for all three calls |
| `max_tokens` (draft/revised) | `600` | ~450 words max per output |
| `max_tokens` (critique) | `400` | Enough for 5-dimension review |

> **Tip:** The `audience` string is the most impactful input. The more specific you are ("Series B SaaS founders in Southeast Asia" vs "startup people"), the more useful the tone critique becomes.

---

## Cost & Performance

| Metric | Value |
|---|---|
| Calls per run | 3 |
| Estimated tokens per run | ~2,900 (in + out combined) |
| **Cost per run** | **~$0.01** |
| 100 runs | ~$1.00 |
| End-to-end latency | 15–30 seconds |

Running this daily for a month costs approximately **$0.30**.

---

## When to Use This Agent

✅ **Good fit:**
- Blog post intros, LinkedIn articles, thought leadership content
- When audience-tone accuracy matters (technical vs. executive vs. regional audiences)
- When you want to understand *why* a draft is weak, not just get a rewrite
- Producing 300-word intros as a starting point for longer pieces

⛔ **Not the right tool for:**
- Full-length articles (1,500+ words) — truncation risk
- Content requiring current data, statistics, or recent events — no web access
- Strict brand voice adherence — no memory of past posts
- Real-time or breaking content
- Non-English language content — critique dimensions are optimised for English

---

## Project Structure

```
blog-post-generator-agent/
├── blog_agent.py              # Main script
├── .env                       # API key (never commit this)
├── .gitignore
├── requirements.txt
│
├── brief/
│   └── AGENT_BRIEF.md         # Phase 1 — Problem, persona, I/O spec
│
├── design/
│   └── DESIGN_DOC.md          # Phase 2 — Architecture, prompts, config
│
├── evals/
│   └── EVAL_SCORECARD.md      # Phase 4 — Test cases, rubric, failure modes
│
└── ops/
    └── OPS_RUNBOOK.md         # Phase 5 — Security, cost, upgrade roadmap
```

The four documents in `brief/`, `design/`, `evals/`, and `ops/` follow the **5-phase agentic AI lifecycle** framework. They're not just documentation — they're the design artefacts that informed every prompt decision in the code.

---

## Security

⚠️ **Before pushing to GitHub:**

- [ ] API key is loaded from `.env`, not hardcoded in the script
- [ ] `.env` is in `.gitignore`
- [ ] Jupyter notebook outputs are cleared (if using `.ipynb`)
- [ ] Anthropic spend limit is set at [console.anthropic.com](https://console.anthropic.com)

---

## Known Limitations

| Limitation | Workaround |
|---|---|
| Revised draft sometimes paraphrases rather than rewrites | Strengthen the reviser prompt to explicitly cross-reference each critique point |
| Critique may truncate on complex topics | Increase critic `max_tokens` from 400 → 600 |
| No quality gate — one pass only | See upgrade roadmap below |
| No web access — stats may be outdated | Manually verify any data claims before publishing |

---

## Upgrade Roadmap

The agent is intentionally minimal. Here's how to extend it, ranked by value-to-effort ratio:

| Upgrade | What It Unlocks | Complexity |
|---|---|---|
| 🔍 **Web search injection** | Current articles/stats grounded into the draft | Low |
| 📄 **Markdown file export** | One-click publishable output | Low |
| 🔁 **Quality score + revision loop** | True iterative reflection — revise until score ≥ threshold | Medium |
| 🎨 **Brand voice input** | Inject your past posts as style examples | Medium |
| 🖥️ **Streamlit UI** | No-code interface for non-technical users | Medium |
| 📢 **Multi-format routing** | One topic → LinkedIn post + email + tweet thread | High |

**The highest-leverage single upgrade:** adding a 4th LLM call that scores the revised draft (0–10 per dimension) and loops back if average < 7. This turns the prompt chain into a genuine ReAct-style agent and is the architectural step that makes the reflection pattern iterative rather than single-pass.

---

## Architecture Decision Log

**Why not LangChain or LangGraph?**
The orchestration logic is 15 lines of Python. Introducing a framework adds dependency weight and debugging complexity that isn't justified at this autonomy level. If a quality-scoring loop is added, that's the point to evaluate LangGraph.

**Why three separate API calls instead of a conversation thread?**
The Producer and Critic need distinct system prompts and personas. A conversation thread would allow the model to "remember" it wrote the draft, reducing critique objectivity. Separate calls enforce the identity separation that makes the reflection pattern work.

**Why `claude-sonnet-4-5` and not Haiku?**
The Critic call is quality-sensitive — vague critique makes the revision step worthless. Sonnet produces more structured, specific, dimension-aware feedback. Haiku is a viable swap for the Producer and Reviser calls if cost is a constraint.

---

## References

- [Anthropic Claude API Documentation](https://docs.anthropic.com)
- [Reflection Design Pattern — Agentic Patterns Reference](https://arxiv.org/abs/2409.12917)
- [LangGraph for iterative reflection workflows](https://www.langchain.com/langgraph)

---

## License

MIT — use freely, improve openly.

---

*Built as a learning project for the agentic AI design patterns curriculum. The goal wasn't just a working script — it was understanding why the Producer–Critic separation is the architectural decision that makes reflection actually work.*
