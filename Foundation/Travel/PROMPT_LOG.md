# Prompt Log — AI Travel Planner
> Phase 3: Build | Foundation Project #01

Track every system prompt version here. One change at a time. This is the most overlooked PM artifact in AI projects — it's the only way to know why your agent improved or regressed.

---

## How to Use This Log

- Every time you change the system prompt or user prompt, add a new version entry
- Record what you changed, why, and what score it got on the eval scorecard
- Never delete old versions — regression is real and you'll want to go back

---

## Version History

### v1.0 — Initial (baseline)
**Date:** 2026-04-07

**System prompt:**
```
You are an expert travel agent specialising in creating personalised travel itineraries.
Your task is to create a detailed, day-by-day travel plan.

IMPORTANT: Format your response EXACTLY like this:

Day 1 - [City/Area Name]
- Activity 1
- Activity 2
- Activity 3

Day 2 - [City/Area Name]
- Activity 1
- Activity 2

Each activity should be a specific, actionable recommendation. Include restaurant names,
landmark names, museums, etc. Make sure activities match the budget tier and traveler interests.
```

**User prompt:**
```
Create a {num_days}-day travel itinerary for:
- Destination: {destination}
- Budget Level: {budget}
- Interests: {interests}
- Traveling with: {companions}

Please include a mix of iconic attractions, hidden gems, dining recommendations,
and local experiences. Make sure the itinerary is realistic and accounts for
travel time between locations.
```

**Parameters:** model=gpt-4o-mini, temperature=0.7, max_tokens=2000

**What worked:**
- Format compliance strong — Day X pattern parsed correctly
- New Delhi luxury output was specific and relevant (real venue names used)
- Calendar export worked first time

**What didn't work:**
- [Fill in after running eval scorecard]

**Eval score:** TC-01: [score]/100 | Average: [score]/100

---

### v1.1 — [Name your change]
**Date:**

**What changed and why:**

**System prompt:**
```
[paste updated prompt here]
```

**Parameters:** model= | temperature= | max_tokens=

**What worked:**

**What didn't work:**

**Eval score:** Average: [score]/100 | Change from v1.0: [+/-]

---

### v1.2 — [Name your change]
**Date:**

**What changed and why:**

**System prompt:**
```
[paste updated prompt here]
```

**Parameters:** model= | temperature= | max_tokens=

**Eval score:** Average: [score]/100 | Change from v1.1: [+/-]

---

## Prompt Engineering Lessons (fill as you go)

| Lesson | Discovered in version |
|---|---|
| | |
| | |
