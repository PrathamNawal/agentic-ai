# Eval Scorecard — Travel Planning Agent
> Phase 2: Stub | Project: Travel Agent with Tool Use
> Status: STUB — criteria defined, not yet scored

---

## Section 1 — Test Case Library

| Test ID | Query | City (inferred) | Month (inferred) | Style (inferred) | Scenario label |
|---|---|---|---|---|---|
| TC-01 | "I want to visit Lisbon in November. Best time and what to do?" | Lisbon | November | — | Happy path: weather + attractions |
| TC-02 | "What's in Tokyo?" | Tokyo | — | — | Edge: minimal — no month, no style |
| TC-03 | "Plan a complete 7-day luxury trip to Bali in August — weather, things to do, and daily budget" | Bali | August | luxury | Edge: complex — all three tools, explicit style |
| TC-04 | "Is Ulaanbaatar worth visiting in January?" | Ulaanbaatar | January | — | Niche: obscure destination, harsh climate question |
| TC-05 | "What will a 5-day mid-range trip to Bangkok cost me?" | Bangkok | — | mid-range | Stress test: budget query with no weather/attractions implied |

---

## Section 2 — Evaluation Rubric

---

### Category 1: Tool Selection Accuracy (30 points)
*Did the agent call the right tools for each query, and only the right tools?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Correct tools called for the query type (weather for weather questions, attractions for sightseeing, budget for cost questions) | 15 | | | | | |
| No unnecessary tool calls (e.g. calling `estimate_budget` when no cost question was asked) | 10 | | | | | |
| All implied tools called — complex queries (TC-03) trigger all three tools | 5 | | | | | |
| **Subtotal** | /30 | | | | | |

---

### Category 2: Response Quality & Synthesis (40 points)
*Is the final response accurate, complete, and well-synthesised from tool outputs?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Response directly answers the user's question (not generic filler) | 10 | | | | | |
| Tool results are woven into a coherent narrative — not just repeated verbatim | 10 | | | | | |
| Response is complete and not truncated (no mid-sentence endings) | 10 | | | | | |
| Response uses appropriate formatting: headers, tables, or bullets where the content warrants it | 10 | | | | | |
| **Subtotal** | /40 | | | | | |

---

### Category 3: Format & Structure Compliance (20 points)
*Does the output meet structural expectations for a chat-based travel assistant?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Response is in markdown (not raw text or JSON) | 5 | | | | | |
| Response length is appropriate to query complexity — not padded, not clipped | 10 | | | | | |
| Tone is conversational and helpful, not robotic | 5 | | | | | |
| **Subtotal** | /20 | | | | | |

---

### Category 4: Edge Case & Error Handling (10 points)
*Does the agent handle incomplete, vague, or unusual inputs gracefully?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Vague queries (TC-02: no month or style) produce a useful best-effort response, not an error or empty output | 5 | | | | | |
| Niche destination (TC-04: Ulaanbaatar) is handled without hallucination or refusal | 5 | | | | | |
| **Subtotal** | /10 | | | | | |

---

## Section 3 — Scoring Summary

| Test Case | Tool Selection /30 | Response Quality /40 | Format /20 | Edge Cases /10 | Total /100 | Pass? |
|---|---|---|---|---|---|---|
| TC-01 | | | | | | ✓ / ✗ |
| TC-02 | | | | | | ✓ / ✗ |
| TC-03 | | | | | | ✓ / ✗ |
| TC-04 | | | | | | ✓ / ✗ |
| TC-05 | | | | | | ✓ / ✗ |
| **Average** | | | | | | |

**Pass threshold:** 70/100 overall; no category below 15/30 (Tool Selection) or 25/40 (Response Quality). Tool selection is the most critical category — an agent that doesn't call the right tools fails regardless of response quality.

---

## Section 4 — Known Failure Modes

*Predicted based on architecture and grounding risks — to be confirmed in Phase 4.*

| Failure | Trigger | Impact | Fix |
|---|---|---|---|
| Agent answers from training data without calling any tools | Query uses phrasing that feels self-answerable to the LLM (e.g. "What is Kyoto famous for?") | Response is ungrounded and bypasses the tool layer entirely | Strengthen system prompt: "Always use tools to answer — do not rely on training data" |
| `estimate_budget` called without a travel style when query is ambiguous | User asks "how much does Bangkok cost?" without specifying budget/mid-range/luxury | Tool call fails or Claude guesses style without telling the user | Add fallback: if style not inferred, Claude should ask the user before calling the tool |
| Response truncated at 1000 tokens for complex multi-tool queries (TC-03) | Long synthesis across all three tools hits `max_tokens` limit | Response ends mid-sentence; user loses key information | Increase `max_tokens` to 2000; add a `stop_reason == "max_tokens"` check with a UI warning |
| Hardcoded budget figures mislead users planning real trips | Any budget query | User makes financial decisions based on static INR figures that don't reflect real costs | Add UI disclaimer on all budget outputs: "Simulated estimate — verify with live sources" |
| Niche cities return generic attraction lists | Query for a city not anticipated by the simulated tool (e.g. Ulaanbaatar, Tbilisi) | Tool returns the same hardcoded five attractions regardless of city | Acceptable in v1 (simulated tools); fix in v2 by replacing with real API |
| Multi-turn context lost if city changes mid-conversation | User asks about Lisbon, then switches to "what about Tokyo?" | Claude may mix context from both cities | Test multi-turn flows explicitly; if observed, add explicit city extraction per turn |
| API key missing or expired | `ANTHROPIC_API_KEY` not set or revoked | Unhandled exception crashes the Streamlit app with a stack trace | Wrap `client.messages.create` in try/except; display a friendly error in the UI |

---

## Section 5 — Prompt Iteration Log

| Version | Change Made | Why | Score Before | Score After |
|---|---|---|---|---|
| v1.0 | Initial prompt: "You are a travel assistant. Use tools to give accurate, specific answers." | Baseline | — | [fill in Phase 4] |
| v1.1 | | | | |
| v1.2 | | | | |
