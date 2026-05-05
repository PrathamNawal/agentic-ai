# Eval Scorecard — Blog Post Generator Agent
> Phase 4: Full | Project: Blog Post Generator Agent
> Status: FULL — scored on real outputs (code has been provided and run)

---

## Section 1 — Test Case Library

| Test ID | topic | audience | Scenario label |
|---|---|---|---|
| TC-01 | "why product managers need to understand AI agents" | "senior product managers at Indian tech companies" | Happy path — original inputs |
| TC-02 | "importance of user research" | "early-stage startup founders" | Edge: minimal — short topic, broad audience |
| TC-03 | "how generative AI is reshaping product roadmaps, prioritisation frameworks, and team structures in enterprise SaaS companies" | "VP of Product at Series B–D SaaS companies in the US managing teams of 10+ PMs across multiple product lines" | Edge: complex — long topic, highly specific audience |
| TC-04 | "why vernacular-language product design matters" | "product designers at Tier 2 Indian city startups building for non-English speakers" | Niche — culturally specific audience, less represented in training data |
| TC-05 | "AI" | "people" | Stress test — maximally vague inputs; most likely to produce generic output and weak critique |

---

## Section 2 — Evaluation Rubric

### Category 1: Critique Quality (30 points)
*Does the Critic call produce specific, actionable, multi-dimensional feedback — not vague platitudes?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| All 5 rubric dimensions addressed (hook, clarity, examples, actionability, tone) | 10 | | | | | |
| At least 3 suggestions are concrete (e.g. "replace X with Y", not "make it better") | 10 | | | | | |
| Critique references audience-specific expectations (not generic writing advice) | 10 | | | | | |
| **Subtotal** | /30 | | | | | |

---

### Category 2: Draft Quality (25 points)
*Does the Producer's first draft show audience awareness and a real opening hook?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Opening sentence is not a generic "AI is changing X" or definition statement | 10 | | | | | |
| Draft is 250–350 words (within configured range) | 5 | | | | | |
| Audience tone is identifiable without being told (blind test) | 10 | | | | | |
| **Subtotal** | /25 | | | | | |

---

### Category 3: Revision Improvement (30 points)
*Does the revised draft genuinely improve on the draft, not just paraphrase it?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Revised draft addresses ≥ 3 specific points raised in the critique | 15 | | | | | |
| Revised draft's opening is meaningfully different from draft's opening | 10 | | | | | |
| Revised draft does not introduce new vague claims not in the critique | 5 | | | | | |
| **Subtotal** | /30 | | | | | |

---

### Category 4: Format & Edge Case Handling (15 points)
*Does the agent handle imperfect inputs gracefully and stay within format bounds?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Critique is 150–300 words (not truncated, not padded) | 5 | | | | | |
| Agent completes all 3 calls without error on this input | 5 | | | | | |
| Vague inputs (TC-05) produce a critique that still names specific weaknesses | 5 | | | | | |
| **Subtotal** | /15 | | | | | |

---

## Section 3 — Scoring Summary

| Test Case | Critique Quality /30 | Draft Quality /25 | Revision Improvement /30 | Format & Errors /15 | Total /100 | Pass? |
|---|---|---|---|---|---|---|
| TC-01 | | | | | | ✓ / ✗ |
| TC-02 | | | | | | ✓ / ✗ |
| TC-03 | | | | | | ✓ / ✗ |
| TC-04 | | | | | | ✓ / ✗ |
| TC-05 | | | | | | ✓ / ✗ |
| **Average** | | | | | | |

**Pass threshold:** 70/100 overall, with no single category below 15/30 (or proportional floor). TC-05 (stress test) pass threshold is lower: 50/100 is acceptable.

---

## Section 4 — Known Failure Modes

| Failure | Trigger | Impact | Fix |
|---|---|---|---|
| Critique collapses to generic advice ("add more examples", "improve tone") | Audience string is vague (e.g. "people"); critic has no specific reader to evaluate tone against | Revision step has no actionable target; draft and revised are nearly identical | Add a validation step: if audience string is < 5 words, prompt user to be more specific before running |
| Revised draft is a light paraphrase, not a rewrite | Critique contains only 1–2 actionable points; reviser has little to work with | User gets marginal value over a single LLM call | Strengthen reviser prompt: "For each numbered critique point, explicitly state how you addressed it in the revised version" |
| max_tokens (400) truncates the critique mid-point | Complex topic with long draft; critique runs long | Dimensions 4–5 (actionability, tone) are missing or cut off | Increase critic max_tokens to 600; accept minor cost increase |
| Draft exceeds 300 words and becomes an introduction + body mixed together | Claude interprets "intro" loosely for complex topics | Revised post is not a true intro; confuses readers | Add explicit word count instruction: "Stop at exactly 300 words. Do not begin a second section." |
| Audience-specific tone is not captured for niche Indian regional contexts | LLM training data underrepresents Tier 2 Indian city tech culture | Tone feels generic-global rather than locally resonant | For niche audiences, add 2–3 example phrases or idioms that match the audience in the system prompt |
| API call fails silently and None is returned | Rate limit hit; network timeout | Downstream calls receive None as input; critique or revised is an empty/confused output | Wrap each `client.messages.create` call in try/except with a meaningful error message |
| Cost unexpectedly high on repeated runs | User runs the script 50+ times during testing without tracking | Unexpected API bill | Add a token counter after each call and a cumulative session cost estimate to the print output |

---

## Section 5 — Prompt Iteration Log

| Version | Change Made | Why | Score Before | Score After |
|---|---|---|---|---|
| v1.0 | Initial prompt — no system prompt on Call 3 (reviser) | Baseline implementation from code | — | Run TC-01 to establish |
| v1.1 | Add explicit numbered critique point cross-reference to reviser prompt | Fix for "light paraphrase" failure mode | — | — |
| v1.2 | Increase critic max_tokens from 400 → 600 | Fix for truncated critique on complex topics | — | — |
| v1.3 | Add word count hard stop to producer prompt | Fix for draft overrun failure | — | — |

---

## Section 6 — PM Reflection

*(Fill in after running all 5 test cases)*

- **Most common failure mode:** *(To be completed after running TC-01 through TC-05)*
- **Worst-performing test case:** *(Expected: TC-05 — vague inputs "AI" + "people" stress test)*
- **Single biggest prompt improvement:** *(Hypothesis: adding numbered cross-reference requirement to reviser prompt will move score most)*
- **What requires architecture change to fix:** The "light paraphrase" failure cannot be fully fixed by prompts alone. A quality-scoring 4th LLM call that compares draft vs revised against the critique dimensions — with a loop exit condition — requires moving to Level 3 (ReAct-style) architecture.
