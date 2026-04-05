# Agent Brief — AI Travel Planner
> Phase 1: Define | Foundation Project #01

---

## 1. Problem Statement

Planning a trip is time-consuming and fragmented. Travellers spend hours across blogs, review sites, and booking apps trying to stitch together a coherent itinerary. The result is often generic, not tailored to their budget, interests, or travel style — and it still doesn't land in their calendar.

**This agent solves:** Give me a complete, personalised day-by-day travel plan in under 60 seconds, and put it directly in my calendar.

---

## 2. User Persona

| Field | Detail |
|---|---|
| **Name** | Casual Traveller (Tier 1 user) |
| **Who** | Working professional, 25–40, plans 2–4 trips/year |
| **Context** | Has a destination and dates in mind, overwhelmed by planning |
| **Tech comfort** | Can run a Jupyter notebook; not a developer |
| **Goal** | Get a ready-to-use itinerary without hours of research |
| **Frustration** | Generic blog listicles that don't match their budget or interests |

---

## 2a. Job-to-be-Done (JTBD)

> **When I** have a trip destination and dates locked but no plan, **I want to** generate a personalised day-by-day itinerary instantly, **so I can** spend my time experiencing the trip — not planning it.

---

## 3. Input / Output Specification

### Inputs (what the user provides)
| Input | Type | Example | Required |
|---|---|---|---|
| `destination` | string | "New Delhi, India" | Yes |
| `num_days` | integer | 5 | Yes |
| `budget` | enum | "low" / "mid" / "luxury" | Yes |
| `interests` | list of strings | ["food", "culture", "history"] | Yes |
| `companions` | enum | "solo" / "couple" / "family" / "group" | Yes |
| `trip_start_date` | date string | "2026-04-07" | Yes |

### Outputs (what the agent produces)
| Output | Format | Description |
|---|---|---|
| Itinerary | Markdown (rendered in notebook) | Day-by-day plan with specific venues |
| Calendar file | `.ics` | Importable into Google/Apple/Outlook Calendar |

---

## 4. Step-by-Step Workflow (plain English)

1. User opens the Jupyter notebook and fills in trip inputs (Cell 3)
2. User runs all cells sequentially
3. Cell 4 builds a system prompt (expert travel agent role) + user prompt (trip details)
4. Agent calls OpenRouter API → GPT-4o-mini processes the prompt
5. API returns a structured itinerary in "Day X - Location / - Activity" format
6. Cell 5 renders the itinerary as rich Markdown in the notebook
7. Cell 6 parses the itinerary text, creates calendar events per day, exports as `.ics`
8. User imports `.ics` into their preferred calendar app

---

## 5. Success Metrics

| Metric | Target | How to Measure |
|---|---|---|
| Itinerary generation time | < 30 seconds | Measure API response time |
| Format compliance | 100% of days parsed correctly | Count Day blocks vs calendar events created |
| Calendar export success | .ics imports without errors | Manual test across Google/Apple/Outlook |
| Output relevance | Activities match budget + interests | Human eval checklist (see Evals doc) |
| User effort | < 5 min from open to calendar export | Time a test run end-to-end |

---

## 6. Constraints & Assumptions

**Constraints**
- Requires an OpenRouter API key (paid, usage-based)
- No real-time data — LLM knowledge cutoff applies (no live flight/hotel prices)
- Requires internet connection
- Python 3.9+ and Jupyter environment needed
- No booking capability — planning only

**Assumptions**
- User has basic ability to run a Jupyter notebook
- Output quality depends on GPT-4o-mini's knowledge of the destination
- Budget tiers are qualitative guides, not price-locked recommendations

---

## 7. Contra-Indicators — When NOT to Use This Agent

| Situation | Why it's unfit | Better alternative |
|---|---|---|
| User needs live prices or availability | LLM has no real-time data; outputs are fictional estimates | Google Flights, Booking.com |
| Trip to a niche / remote destination | LLM training data is sparse; hallucination risk is high | Local travel forums, human agent |
| User wants to refine iteratively ("change Day 3") | Single-shot agent; no memory or conversation | Multi-turn agent (future upgrade) |
| Compliance-sensitive travel (visa, health advisories) | LLM may be outdated or wrong on regulations | Official government sources |
| User expects agent to book anything | No transaction capability whatsoever | Booking tools with API integrations |

---

## 8. Data Grounding & Freshness

| Dimension | Detail |
|---|---|
| **Data source** | GPT-4o-mini training data (no live retrieval) |
| **Knowledge cutoff** | Model cutoff applies — venues may have closed, prices changed, hours shifted |
| **Grounding method** | None in v1 — output is entirely LLM-generated, not verified against live sources |
| **Freshness risk** | High for fast-changing info (restaurant closures, hotel rebranding); low for landmarks |
| **Mitigation for user** | Output includes implicit disclaimer; user should verify critical details before travel |
| **Upgrade path** | Add Tavily/SerpAPI web search tool so agent retrieves live venue data before generating itinerary |

---

## 9. Top 3 Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **LLM hallucinates venue details** — recommends restaurants that are closed, wrong addresses, fabricated names | Medium | Medium — user plans around bad info | Add output disclaimer; future upgrade adds web search grounding |
| **API key exposed via GitHub commit** — hardcoded key in notebook gets pushed publicly | High (without care) | Medium — unexpected charges on OpenRouter account | Use `os.environ.get()`, add `.env` to `.gitignore`, clear notebook outputs before commit |
| **Format breaks, calendar export fails silently** — LLM deviates from "Day X - Location" format, ICS parser creates 0 events with no error | Medium | Low — itinerary still visible in Markdown | Add event count validation after export; add format example to system prompt |

---

## 10. Learning Objectives (PM lens)

What this project teaches about the AI agent lifecycle:

- How to structure a system prompt vs user prompt
- How to configure LLM parameters (temperature, max_tokens)
- How to parse LLM output programmatically (regex on structured text)
- Difference between a **single LLM call** and a true **agentic loop**
- Why this is a "Level 1" agent — no tools, no memory, no loops

> **Key insight for this project:** This is technically a *prompt chain*, not a full agent. A true agent would use tools (web search for live prices, maps API for travel time). This is a great baseline to upgrade in later projects.
