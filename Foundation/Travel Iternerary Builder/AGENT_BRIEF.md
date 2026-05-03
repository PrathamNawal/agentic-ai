# Agent Brief — Travel Itinerary Builder
> Phase 1: Define | Travel Itinerary Builder Agent
> Status: Complete

---

## Section 1 — Problem Statement

Planning a multi-day trip requires hours of research across blogs, review sites, and travel forums — most travellers cobble together a rough list of places but struggle to turn that into a logical, day-by-day schedule that respects pacing, geography, and budget. The current workaround is either paying a travel agent or spending an entire weekend manually sequencing activities.

**This agent solves:** A traveller provides their destination, duration, style, and budget in one sentence, and receives a complete, day-by-day written itinerary with top experiences, timings, and costs — in under 30 seconds.

---

## Section 2 — User Persona

| Field | Detail |
|---|---|
| Name | Independent Trip Planner |
| Who | 25–45 year old traveller, plans 2–4 trips per year, typically solo or with a partner |
| Context | 2–6 weeks before departure, has a destination in mind but no structure yet |
| Tech comfort | Comfortable typing a sentence; does not want to fill in a form or learn a tool |
| Goal | Get a concrete, ready-to-use itinerary that removes decision fatigue |
| Frustration | Every "itinerary guide" online is generic, ad-stuffed, or doesn't match their travel style |

---

## Section 2a — Job-to-be-Done (JTBD)

> **When I** have a destination and a trip window but no plan, **I want to** describe my trip in one sentence and receive a structured day-by-day itinerary, **so I can** stop researching and start booking.

---

## Section 3 — Input / Output Specification

**Inputs:**

| Input | Type | Example | Required |
|---|---|---|---|
| destination | string | "Kyoto, Japan" | Yes |
| duration_days | integer | 5 | Yes |
| travel_style | string (free text) | "temples and food" / "adventure and nightlife" | Yes |
| budget_level | enum: budget / mid-range / luxury | "mid-range" | Yes |

**Outputs:**

| Output | Format | Description |
|---|---|---|
| Parsed profile | JSON | Structured extraction of destination, days, style, budget |
| Experience list | JSON list | Top 5 must-do experiences with name, hours, cost_level |
| Day schedule | JSON | Day-by-day activity allocation |
| Final itinerary | Markdown prose | Friendly, detailed travel narrative the user can read and act on |

---

## Section 4 — Step-by-Step Workflow (Plain English)

1. User types a single natural-language request: destination, duration, interests, and budget level.
2. Agent sends the request to **Step 1: Parse** — extracts structured JSON (destination, duration_days, travel_style, budget_level).
3. Agent sends the parsed profile to **Step 2: Research** — generates a JSON list of the top 5 must-do experiences matched to the travel style and budget.
4. Agent sends parsed profile + experiences to **Step 3: Schedule** — produces a logical day-by-day JSON schedule, grouping experiences sensibly by geography and pacing.
5. Agent sends the schedule to **Step 4: Write** — converts structured JSON into a warm, readable, prose travel itinerary.
6. Agent prints all four outputs: parsed profile, experiences, schedule, and the final itinerary.
7. User reads the final itinerary and uses it directly or copies it into a notes app for their trip.

---

## Section 5 — Success Metrics

| Metric | Target | How to Measure |
|---|---|---|
| End-to-end latency | < 30 seconds for a 5-day trip | Time from request submission to final print |
| Parse accuracy | Correct extraction in ≥ 95% of natural-language inputs | Manual check of parsed JSON against input |
| Experience relevance | ≥ 4 of 5 experiences match the stated travel style | Human rater scores each experience |
| Schedule logic | Days are geographically coherent and not overloaded | Human rater checks clustering and total daily hours |
| Itinerary readability | Output reads as a complete, usable trip plan | Human rates on 1–5 scale; target ≥ 4.0 |

---

## Section 6 — Constraints & Assumptions

**Constraints:**
- No real-time data: cannot check live prices, opening hours, or booking availability
- No tool use in v1: all knowledge comes from LLM training data
- Chain is sequential: each step must complete before the next begins (no parallelism)
- Max output bounded by `max_tokens` per step — very long trips (10+ days) may truncate
- API key must be set in the environment — agent cannot run without it
- Model knowledge cutoff applies: new attractions, restaurant closures, and visa changes may not be reflected

**Assumptions:**
- User provides a valid, real destination
- Travel style and budget level are expressible in everyday English
- The destination is well-represented in LLM training data (popular travel destinations perform better than obscure ones)
- The user will validate the itinerary before booking — this is a starting point, not a booking engine

---

## Section 7 — Contra-Indicators (When NOT to Use This Agent)

| Situation | Why it's unfit | Better alternative |
|---|---|---|
| Booking flights, hotels, or tours | Agent produces text only — no booking capability | Use Google Flights, Booking.com, or a travel agent |
| Real-time pricing or availability | LLM knowledge is not live — prices/hours may be wrong | Use TripAdvisor, Google Maps, or destination websites |
| Visa and entry requirements | Regulations change frequently and errors carry legal risk | Check official government or embassy websites |
| Hyper-niche destinations with sparse LLM coverage | May hallucinate or produce generic output | Use local travel blogs, subreddits, or destination experts |
| Complex logistics (multi-city routing, transit visas) | Sequential chain cannot reason over constraints dynamically | Use a human travel planner or a ReAct-based agent with routing tools |
| Accessibility or medical requirements | High-stakes personalisation requires verified data | Consult a specialist travel service |

---

## Section 8 — Data Grounding & Freshness

| Dimension | Detail |
|---|---|
| Data source | LLM training data (Claude's knowledge of travel destinations) |
| Knowledge cutoff | Claude Sonnet has a training cutoff; newly opened venues, closed businesses, and changed entry rules will not be reflected |
| Grounding method | None in v1 — no RAG, no web search, no external database |
| Freshness risk | **Medium** — popular destination core experiences (temples, cuisine districts, major museums) are stable; new restaurants or current pricing are high-risk |
| Mitigation | Add a disclaimer in the final output that users should verify prices, hours, and availability before booking |
| Upgrade path | Add web search tool to Research step so the agent fetches live review data; or RAG over a curated travel knowledge base |

---

## Section 9 — Top 3 Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| JSON parse failure — LLM deviates from format, breaking the chain | Medium | High — downstream steps receive garbled input and produce unusable output | Add explicit format examples in each system prompt; wrap each step in try/except with fallback handling |
| Hallucinated experiences — LLM invents a plausible-sounding but non-existent attraction | Medium | Medium — user wastes time researching a fake venue | Add a disclaimer to final output; upgrade to web-search grounding in v2 |
| Token truncation — long trips exceed max_tokens, producing cut-off schedules | Low | Medium — final day(s) missing from itinerary | Increase max_tokens per step; add a token estimation check before sending |

---

## Section 10 — Learning Objectives (PM Lens)

- **Prompt engineering concept demonstrated:** Multi-step prompt chaining — each step is a focused prompt with a single responsibility (parse / research / schedule / write), which dramatically improves output quality over a single mega-prompt.
- **LLM parameter made concrete:** `max_tokens` as a real constraint — each step has a ceiling that forces trade-offs between depth and completeness.
- **Key architectural insight:** This is a **prompt chain, not a true agent** — there is no loop, no tool use, no dynamic decision-making. The LLM executes a fixed pipeline. Recognising this boundary is the most important skill in agentic AI design.
- **Natural next level:** Adding a validation step between parse → research that checks for hallucinations, or adding web search to the research step, would elevate this to a Level 3 ReAct agent.

> **Key insight for this project:** Prompt chaining teaches you that decomposing a hard task into sequential focused prompts almost always outperforms a single "do everything" prompt — and understanding *why* that is true is the foundation of all agentic design.
