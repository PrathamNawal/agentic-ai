# Eval Scorecard — Travel Itinerary Builder
> Phase 2: Stub | Travel Itinerary Builder Agent
> Status: STUB — criteria defined, not yet scored

---

## Section 1 — Test Case Library

| Test ID | Destination | Duration (days) | Travel Style | Budget Level | Scenario Label |
|---|---|---|---|---|---|
| TC-01 | Kyoto, Japan | 5 | temples and food | mid-range | Happy path |
| TC-02 | Paris, France | 2 | art and cafés | budget | Edge: minimal (short trip) |
| TC-03 | New Zealand | 14 | hiking, adventure, wildlife, local food, road trips | luxury | Edge: complex (long trip, multi-interest) |
| TC-04 | Tbilisi, Georgia | 4 | wine, history, off-the-beaten-path | mid-range | Niche (less common LLM destination) |
| TC-05 | !! Go anywhere amazing 🎉🌍 | 3 | everything!! | any | Stress test (malformed/ambiguous input) |

---

## Section 2 — Evaluation Rubric

---

### Category 1: Format & Structure Compliance (25 points)
*Measures whether all four pipeline steps return correctly structured, parseable output that allows the chain to complete without crashing.*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Parse step returns valid JSON with all 4 required fields (destination, duration_days, travel_style, budget_level) | 7 | | | | | |
| Research step returns valid JSON list with exactly 5 entries, each containing name, duration_hours, cost_level | 8 | | | | | |
| Schedule step returns valid JSON with the correct number of day keys matching duration_days | 5 | | | | | |
| Write step returns readable prose (not JSON, not empty, not truncated mid-sentence) | 5 | | | | | |
| **Subtotal** | /25 | | | | | |

---

### Category 2: Output Quality & Relevance (40 points)
*Measures whether the content of each step is accurate, relevant to the user's stated interests, and practically useful.*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| At least 4 of 5 experiences clearly match the stated travel style | 10 | | | | | |
| No experience appears to be hallucinated (verifiably exists in the destination) | 10 | | | | | |
| Schedule groups activities logically — no single day exceeds a realistic 10-hour activity window | 8 | | | | | |
| Final itinerary covers every day listed in the schedule | 7 | | | | | |
| Final itinerary includes practical detail: timing estimates and cost-level cues | 5 | | | | | |
| **Subtotal** | /40 | | | | | |

---

### Category 3: Chain Integrity (20 points)
*Measures whether intermediate outputs successfully propagate through the chain without manual intervention.*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Chain completes all 4 steps without a Python exception or empty output | 10 | | | | | |
| Schedule step correctly uses both the parsed profile and the experience list (not just one) | 5 | | | | | |
| Write step references specific experiences from the schedule (not generic placeholders) | 5 | | | | | |
| **Subtotal** | /20 | | | | | |

---

### Category 4: Edge Case & Error Handling (15 points)
*Measures graceful handling of non-standard or ambiguous inputs.*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Agent produces useful output even when destination is less-common / niche (TC-04) | 5 | | | | | |
| Agent does not crash on ambiguous or malformed input (TC-05) — produces partial output or sensible fallback | 5 | | | | | |
| Long-trip output (TC-03) covers all 14 days without truncation | 5 | | | | | |
| **Subtotal** | /15 | | | | | |

---

## Section 3 — Scoring Summary

| Test Case | Format /25 | Quality /40 | Chain /20 | Edge /15 | Total /100 | Pass? |
|---|---|---|---|---|---|---|
| TC-01 | | | | | | ✓ / ✗ |
| TC-02 | | | | | | ✓ / ✗ |
| TC-03 | | | | | | ✓ / ✗ |
| TC-04 | | | | | | ✓ / ✗ |
| TC-05 | | | | | | ✓ / ✗ |
| **Average** | | | | | | |

**Pass threshold:** 70/100 overall; no individual category below 50% of its points.
*Rationale: Format and chain integrity are binary blockers — a 50% floor here catches cases where the chain technically runs but produces structurally broken output.*

---

## Section 4 — Known Failure Modes

*Predicted from architecture and grounding risks in Phase 1 and Phase 2. Fill in actual observations during Phase 4.*

| Failure | Trigger | Impact | Fix |
|---|---|---|---|
| Parse returns prose instead of JSON | Ambiguous or very short input; LLM adds explanatory text before the JSON | Research step receives malformed input and either crashes or produces garbled experiences | Strengthen system prompt: add "Do not include any text before or after the JSON object" and provide a one-shot JSON example |
| Research list has fewer or more than 5 entries | Niche destination with limited LLM knowledge; or prompt misread | Schedule step receives incomplete or over-stuffed experience list | Add explicit instruction: "Return exactly 5 items. If fewer exist, complete the list with nearby alternatives." |
| Schedule day count doesn't match duration_days | Long trips (10+ days) hit token limit and truncation cuts the JSON mid-object | Final day(s) missing; write step produces incomplete itinerary | Increase max_tokens on schedule step to 1000+ for trips > 7 days; add a token estimation check |
| Write step repeats the schedule verbatim | Low-temperature setting causes the write step to echo JSON labels as prose | Itinerary reads like a list of labels, not a travel narrative | Raise write step temperature to 0.7–0.9; add "Write in a warm, first-person voice — do not repeat JSON keys" to system prompt |
| Hallucinated experience for niche destination | Obscure destination with sparse LLM training data (e.g. TC-04) | User researches a non-existent venue; trust damage | Add web search tool to Research step in v2; add disclaimer in final output |
| JSON parse error from escaped characters | Destination or activity name contains special characters (apostrophes, non-ASCII) | Downstream `json.loads()` call throws exception and chain crashes | Wrap each step's output in a try/except with a clean error message; strip markdown fences before parsing |
| Budget level ignored in experience selection | Prompt doesn't strongly enforce budget constraint in Research step | Luxury experiences recommended for budget travellers | Add "Only include experiences appropriate for a {budget_level} traveller" to the Research user prompt |

---

## Section 5 — Prompt Iteration Log

| Version | Change Made | Why | Score Before | Score After |
|---|---|---|---|---|
| v1.0 | Initial prompts as written in the code | Baseline | — | [fill in Phase 4] |
| v1.1 | | | | |
| v1.2 | | | | |

---

## Section 6 — PM Reflection

*To be completed in Phase 4 after real test runs.*

- **Most common failure mode:** [fill after testing]
- **Worst-performing test case:** [fill after testing]
- **Single biggest prompt improvement:** [fill after testing]
- **What requires architecture change to fix:** [fill after testing — i.e. what prompt changes alone cannot solve]
