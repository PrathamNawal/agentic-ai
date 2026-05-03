# Eval Scorecard — Parallel Research Agent
> Phase 4: Full | Project: research-agent
> Status: FULL — criteria defined from design; score columns ready for real test runs

---

## Section 1 — Test Case Library

| Test ID | topic | Scenario label |
|---|---|---|
| TC-01 | "generative AI in Indian enterprises" | Happy path — topical, mid-length, well-represented in training data |
| TC-02 | "climate tech" | Edge: minimal — 2 words, highly broad topic |
| TC-03 | "impact of the US CHIPS Act on Southeast Asian semiconductor supply chains in 2024" | Edge: complex — long, specific, multi-regional, time-anchored |
| TC-04 | "vertical AI agents for tier-2 insurance brokers in MENA" | Niche — specific sub-vertical, regional, underrepresented in LLM training |
| TC-05 | "a" | Stress test — single character input; tests graceful degradation |

---

## Section 2 — Evaluation Rubric

### Category 1: Format & Structure Compliance (25 points)
*Does the agent produce outputs in the expected format across all calls?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Each research call returns a numbered list (1. 2. 3.) | 5 | | | | | |
| Exactly 3 insights returned per angle (not 2, not 4) | 5 | | | | | |
| Synthesis returns exactly 3 paragraphs | 5 | | | | | |
| No raw JSON, error tracebacks, or metadata leaked into output | 5 | | | | | |
| Wall clock time ≤ 10 seconds (print timing confirms) | 5 | | | | | |
| **Subtotal** | /25 | | | | | |

---

### Category 2: Output Quality & Insight Depth (40 points)
*Are the outputs substantively useful — specific, multi-angle, and integrated?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Market angle names at least one concrete opportunity (market size, segment, or named company/trend) | 8 | | | | | |
| Risk angle names at least one specific, non-trivial risk (not just "there are challenges") | 8 | | | | | |
| Technology angle names a specific technology, platform, or mechanism — not generic "AI" | 8 | | | | | |
| Synthesis weaves all three angles together (not just 3 sequential paragraphs restating each angle) | 8 | | | | | |
| Synthesis is readable by a non-expert without being condescending | 8 | | | | | |
| **Subtotal** | /40 | | | | | |

---

### Category 3: Error Handling & Resilience (20 points)
*Does the agent handle failures gracefully without crashing or misleading the user?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| Agent reports how many of 3 angles succeeded (e.g. "Got 3/3 perspectives") | 5 | | | | | |
| If one angle fails (simulated), synthesis still completes on remaining angles | 5 | | | | | |
| TC-05 ("a") does not crash — returns some output even for degenerate input | 5 | | | | | |
| No silent failure — exception is caught and excluded from `clean` list | 5 | | | | | |
| **Subtotal** | /20 | | | | | |

---

### Category 4: Grounding & Freshness Honesty (15 points)
*Does the agent set correct expectations about knowledge recency?*

| Check | Points | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 |
|---|---|---|---|---|---|---|
| For TC-03 (time-anchored topic "2024"), agent does not confidently assert stale facts as current | 8 | | | | | |
| For TC-04 (niche topic), agent does not hallucinate named companies or statistics that sound specific but are unverifiable | 7 | | | | | |
| **Subtotal** | /15 | | | | | |

---

## Section 3 — Scoring Summary

| Test Case | Format /25 | Quality /40 | Resilience /20 | Grounding /15 | Total /100 | Pass? |
|---|---|---|---|---|---|---|
| TC-01 | | | | | | ✓ / ✗ |
| TC-02 | | | | | | ✓ / ✗ |
| TC-03 | | | | | | ✓ / ✗ |
| TC-04 | | | | | | ✓ / ✗ |
| TC-05 | | | | | | ✓ / ✗ |
| **Average** | | | | | | |

**Pass threshold:** 70/100 overall, no category below 12/25 (format), 28/40 (quality), 12/20 (resilience), 8/15 (grounding).

---

## Section 4 — Known Failure Modes

| Failure | Trigger | Impact | Fix |
|---|---|---|---|
| Synthesis restates angles sequentially rather than integrating them | Synthesis system prompt is too weak; LLM defaults to listing | User gets a worse-formatted research digest, not an integrated brief | Strengthen synthesis prompt: "Do NOT summarise each angle separately. Weave all three perspectives into a unified narrative." |
| Research call returns 2 or 4 insights instead of 3 | LLM ignores "numbered list" format instruction for vague topics | Format compliance check fails; synthesis sees inconsistent input | Add explicit instruction: "Return exactly 3 insights. No more, no less. Format: 1. [insight] 2. [insight] 3. [insight]" |
| TC-05 ("a") produces confident-sounding but meaningless insights | Degenerate input passes to LLM without validation | User trusts output on garbage input | Add input validation: `if len(topic.strip()) < 5: raise ValueError("Topic too short")` |
| Niche topic (TC-04) produces hallucinated named companies or statistics | LLM fills gaps in training data with plausible-sounding fabrications | User acts on false information | Add grounding disclaimer to synthesis output; upgrade to web search for domains where specificity is critical |
| Token budget (300) cuts off the third insight mid-sentence | Topic generates verbose insights that exceed token limit | User sees incomplete numbered list; synthesis receives truncated input | Increase research `max_tokens` to 400; or add output check for truncation (e.g. detect if last insight ends without punctuation) |
| One angle call silently fails and synthesis runs on 2 angles | API timeout, rate limit, or network error | User gets unbalanced synthesis without knowing market/risk/tech view was missing | Surface angle count in output prominently; consider raising exception if < 2 angles succeed |
| Wall clock time exceeds 10 seconds | API latency spike, especially for complex topics | User frustration; agent feels slow | Add per-call timeout with `asyncio.wait_for()`; log individual call durations |

---

## Section 5 — Prompt Iteration Log

| Version | Change Made | Why | Score Before | Score After |
|---|---|---|---|---|
| v1.0 | Initial prompt — "Give 3 key insights about: {topic}. Use a numbered list." | Baseline | — | [run to score] |
| v1.1 | | | | |
| v1.2 | | | | |

---

## Section 6 — PM Reflection (Complete after first full test run)

- **Most common failure mode:** *(Fill after running TC-01 through TC-05)*
- **Worst-performing test case:** *(Expected: TC-04 niche or TC-05 stress test)*
- **Single biggest prompt improvement:** *(Hypothesis: strengthening synthesis integration instruction)*
- **What requires architecture change to fix:** Fresh data (TC-03, TC-04) cannot be fixed by prompt alone — requires web search tool at Level 3.
