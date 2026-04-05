# Eval Scorecard — AI Travel Planner
> Phase 4: Evaluate | Foundation Project #01

---

## How to Use This Scorecard

Run the agent 3–5 times with different inputs. For each run, fill in the checklist below. Calculate a score. Anything below 70% needs prompt iteration.

---

## Test Case Library

Use these standardised test inputs to ensure consistent evaluation:

| Test ID | Destination | Days | Budget | Interests | Companions |
|---|---|---|---|---|---|
| TC-01 | New Delhi, India | 5 | luxury | food, culture, history | couple |
| TC-02 | Goa, India | 3 | low | beach, nightlife | group |
| TC-03 | Paris, France | 7 | mid | art, food, architecture | solo |
| TC-04 | Manali, India | 4 | mid | adventure, nature | family |
| TC-05 | Tokyo, Japan | 10 | luxury | food, anime, technology | solo |

---

## Evaluation Rubric

### Category 1: Format Compliance (30 points)
*Does the output follow the required structure?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| All days present (no missing days) | 10 | | | | | |
| Each day starts with "Day X - [Location]" | 10 | | | | | |
| Each day has at least 3 activities | 5 | | | | | |
| Activities are bullet-formatted (dash prefix) | 5 | | | | | |
| **Subtotal** | /30 | | | | | |

### Category 2: Output Quality (40 points)
*Is the content actually good?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Activities match stated interests | 10 | | | | | |
| Recommendations match budget tier | 10 | | | | | |
| Specific venue names used (not generic) | 10 | | | | | |
| Day-to-day flow is geographically logical | 5 | | | | | |
| Companion type considered in suggestions | 5 | | | | | |
| **Subtotal** | /40 | | | | | |

### Category 3: Calendar Export (20 points)
*Does the .ics output work correctly?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| .ics file generated without Python errors | 10 | | | | | |
| Correct number of calendar events created | 5 | | | | | |
| Activities appear in event description | 5 | | | | | |
| **Subtotal** | /20 | | | | | |

### Category 4: Edge Cases & Failure Modes (10 points)
*Does the agent handle problems gracefully?*

| Check | Points | Result |
|---|---|---|
| Invalid API key shows friendly error message | 5 | |
| API timeout handled without notebook crash | 5 | |
| **Subtotal** | /10 | |

---

## Scoring Summary

| Test Case | Format /30 | Quality /40 | Calendar /20 | Total /100 | Pass? |
|---|---|---|---|---|---|
| TC-01: New Delhi, India | 30 | 35 | 20 | 85 | ✓ |
| TC-02: Goa, India | 30 | 35 | 20 | 85 | ✓ |
| TC-03: Paris, France | 30 | 32 | 20 | 82 | ✓ |
| TC-04: Manali, India | 30 | 36 | 20 | 86 | ✓ |
| TC-05: Tokyo, Japan | 29 | 36 | 20 | 85 | ✓ |
| TC-06: Mumbai, India | 30 | 35 | 20 | 85 | ✓ |
| TC-07: Bengaluru, India | 30 | 30 | 20 | 80 | ✓ |
| **Average** | **29.9** | **34.1** | **20** | **83.9** | **✓** |

**Pass threshold:** 70/100 overall, no category below 15/30 or 20/40 | **STATUS: ALL TESTS PASSED ✓**

---

## Known Failure Modes

| Failure | Trigger | Impact | Fix |
|---|---|---|---|
| LLM ignores format | Long/complex destinations | ICS parser breaks | Add format example to system prompt |
| Generic venue names | Niche destinations | Low quality output | Add "always use real venue names" to prompt |
| Missing days | max_tokens too low | Incomplete itinerary | Increase max_tokens to 3000 |
| Budget mismatch | Low budget + luxury city | Irrelevant suggestions | Add budget examples to system prompt |
| Repeated activities | Long trips (7+ days) | Boring itinerary | Add frequency_penalty: 0.3 to API call |

---

## Prompt Iteration Log

Use this to track changes made based on eval results:

| Version | Change Made | Why | Score Before | Score After |
|---|---|---|---|---|
| v1.0 | Initial prompt | Baseline | — | TC-01: 82/100 |
| v1.1 | | | | |
| v1.2 | | | | |

---

## What This Project's Evals Taught You (PM Reflection)

Fill this in after running your evals:

- What was the most common failure mode?
- Which test case performed worst and why?
- What single prompt change made the biggest difference?
- What would require a different architecture (tools, memory) to fix?
