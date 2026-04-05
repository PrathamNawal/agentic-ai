# Agentic AI PM Skills
> Reusable skill files for the 5-phase agent lifecycle | Pratham Nawal

These 4 skills produce the PM documentation artifacts for every agent project in this repo. Use them in sequence — each builds on the previous.

---

## How to Use

When starting a new agent project, work through the skills in order. Each skill tells you exactly what input it needs and what it produces.

| Phase | Skill | Input | Output | Timing |
|---|---|---|---|---|
| 1 — Define | `agent-brief/SKILL.md` | Agent idea + user context | `brief/AGENT_BRIEF.md` | Before any code |
| 2 — Design | `design-doc/SKILL.md` | Completed Agent Brief | `design/DESIGN_DOC.md` + eval stub | Before any code |
| 3 — Build | *(no skill — you build)* | Design Doc | `travel_agent.ipynb` + `build/PROMPT_LOG.md` | Build phase |
| 4 — Evaluate | `eval-scorecard/SKILL.md` | Code + real outputs | `evals/EVAL_SCORECARD.md` (full) | After first working run |
| 5 — Operate | `ops-runbook/SKILL.md` | Brief + Design + Eval | `ops/OPS_RUNBOOK.md` | After evals complete |

---

## Key Principles Baked Into Every Skill

**Code comes late.** Brief and Design require zero code. This forces product thinking before implementation.

**Two-stage evals.** The Eval Scorecard is stubbed in Phase 2 (what does good look like?) and completed in Phase 4 (did we hit it?). Never evaluate against vibes.

**Architecture decision is explicit.** Every Design Doc forces a deliberate choice of autonomy level (1–4) with a written rationale. You can't accidentally over-engineer or under-engineer.

**Next Level is a first-class artifact.** Every Ops Runbook ends with a specific upgrade tied to a failing eval. Projects connect to each other.

**Prompt Log is mandatory.** Every build phase has a PROMPT_LOG.md. One change at a time, always logged.

---

## Folder Structure Per Project

```
[Project Name]/
├── README.md
├── [agent_code].ipynb or .py
├── brief/
│   └── AGENT_BRIEF.md          ← Phase 1 output
├── design/
│   └── DESIGN_DOC.md           ← Phase 2 output (includes eval stub)
├── build/
│   └── PROMPT_LOG.md           ← Phase 3 artifact
├── evals/
│   └── EVAL_SCORECARD.md       ← Phase 4 output (stub from Phase 2, scored here)
└── ops/
    └── OPS_RUNBOOK.md          ← Phase 5 output
```

---

## Skills Folder Structure

```
skills/
├── README.md                   ← This file
├── agent-brief/
│   └── SKILL.md
├── design-doc/
│   └── SKILL.md
├── eval-scorecard/
│   └── SKILL.md
└── ops-runbook/
    └── SKILL.md
```
