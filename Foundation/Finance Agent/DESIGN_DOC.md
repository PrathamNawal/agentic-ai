# Design Document: YFinance Market Research Agent
**Phase 2 — Design**

---

## Section 1 — Agent Architecture Classification

| Dimension | This Agent | Why |
|---|---|---|
| Pattern | Single LLM call (deterministic pipeline) | Query is straightforward: parse input → fetch data → format output. No iterative reasoning needed. |
| Memory | None | Single-shot interaction; each query is independent. No conversation history to retain. |
| Tools | YFinanceTools (single, unified) | One data source, one tool. Simple and focused. |
| Autonomy level | Level 1: Single LLM call | Input goes to LLM with context, LLM calls tool via tool use, formats response, returns. No loops or multi-step reasoning. |
| Upgrade path | Level 2 (Prompt chain) to support multi-turn follow-ups, or Level 3 (ReAct loop) if agent needs to iteratively refine queries or combine multiple data sources. |

---

## Section 2 — Architecture Decision

| Level | Pattern | Description | This agent? |
|---|---|---|---|
| 1 | Single LLM call | One prompt in, one response out | ✅ **CHOSEN** |
| 2 | Prompt chain | Sequential calls, output feeds next | ❌ |
| 3 | ReAct loop | LLM reasons, picks tool, observes, repeats | ❌ |
| 4 | Multi-agent | Orchestrator delegates to specialists | ❌ |

**Decision Rationale:**

- **Why Level 1 is right:** The agent's job is deterministic: parse a query, fetch matching data from YFinance, and format it. No dynamic reasoning loop, no multi-step planning, no uncertainty about which tool to call. The LLM's tool use feature (single call to YFinanceTools) is sufficient.

- **What would require going higher:** Multi-turn conversation (user asks follow-up → agent refines), iterative refinement (agent tries query, sees missing data, retries with adjusted params), or multiple independent data sources (stocks + news + macro indicators) would push to Level 2 or 3.

- **What complexity this avoids:** No state management, no loop tracking, no call history retention. Each query is independent and complete, keeping the system fast and predictable.

---

## Section 3 — Workflow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        DESIGN DOC WORKFLOW: DATA FLOW                        │
└──────────────────────────────────────────────────────────────────────────────┘

                            ┌─────────────────┐
                            │  Jupyter User   │
                            │  Input Query    │
                            └────────┬────────┘
                                     │
                 ┌───────────────────▼───────────────────┐
                 │  1. Query Ingestion & Validation      │
                 │  • User provides query string          │
                 │  • Validate format (not empty, etc.)   │
                 └───────────────────┬───────────────────┘
                                     │
                 ┌───────────────────▼───────────────────┐
                 │  2. Build Context & System Prompt     │
                 │  • System: Role, guardrails, format   │
                 │  • Current timestamp, instructions    │
                 └───────────────────┬───────────────────┘
                                     │
                 ┌───────────────────▼───────────────────┐
                 │  3. LLM Receives Full Context         │
                 │  • System prompt (role + guardrails)  │
                 │  • User query                         │
                 │  • Tool definitions (YFinanceTools)   │
                 └───────────────────┬───────────────────┘
                                     │
                 ┌───────────────────▼──────────────────────────────────┐
                 │  4. LLM Processes & Decides                          │
                 │  • Parse query: tickers, scope, depth                │
                 │  • Check guardrails (buy/sell? crypto?)              │
                 │  • If safe: invoke YFinanceTools, else: refuse       │
                 └───────────────────┬──────────────────────────────────┘
                                     │
                 ┌─────────────┬─────┴─────┬──────────────┐
                 │             │           │              │
        ┌────────▼────┐  ┌─────▼──────┐  ┌▼──────────┐  ┌▼──────────────┐
        │  Fetch Data │  │   Refuse   │  │Edge Case  │  │ Unclear Query │
        │ YFinance    │  │ (Guardrail)│  │ (Missing) │  │ (Ask user)    │
        │ • Price     │  │ • Reframe  │  │ • Log gap │  │ • Suggest     │
        │ • P/E, EPS  │  │ • Context  │  │ • Continue│  │   tickers     │
        │ • Cap, etc  │  │ • Explain  │  │ • Self-   │  │ • Clarify     │
        └────────┬────┘  └─────┬──────┘  │   help    │  │   scope       │
                 │             │         └▼──────────┘  └▼──────────────┘
                 │             │              │              │
                 └─────────────┼──────────────┼──────────────┘
                               │
                 ┌─────────────▼──────────────────────┐
                 │  5. Analyze & Format Response      │
                 │  • Compute ratios if needed        │
                 │  • Identify trends                 │
                 │  • Choose format (table/narrative) │
                 │  • Add timestamp & source          │
                 └─────────────┬──────────────────────┘
                               │
                 ┌─────────────▼──────────────────────┐
                 │  6. Return Single-Shot Response    │
                 │  • Markdown (no JSON)              │
                 │  • Complete & self-contained       │
                 │  • Displayed in Jupyter output     │
                 └─────────────┬──────────────────────┘
                               │
                            ┌──▼────────────┐
                            │   Advisor     │
                            │   Receives    │
                            │   Analysis    │
                            └───────────────┘
```

**Critical Path:** Query → LLM + System Prompt → YFinanceTools call → Format → Return (all in one LLM invocation)

---

## Section 4 — Agent Configuration Sheet

### 4a. Model Parameters

| Parameter | Value | Rationale |
|---|---|---|
| Model | Claude 3 Haiku (via OpenRouter) | Smallest, fastest, cheapest model. Financial data queries are straightforward; don't need Sonnet's reasoning power. Cost optimization aligns with brief. |
| Temperature | 0.0 (deterministic) | Financial data must be precise, not creative. No hallucination acceptable. Deterministic parsing and formatting required. |
| Max tokens | 2000 | Typical responses: quick lookup ~200 tokens, deep dive with table ~800–1200 tokens. 2000 provides buffer for large comparisons (5+ stocks). |
| Timeout | 10 seconds | YFinance API typically responds <2s; LLM processing <3s. 10s total provides headroom without hanging. |
| Top-p | Default (0.9) | Temperature is the primary control; top-p at default is sufficient. |
| Frequency penalty | Not set (0.0) | No need to discourage repetition; output is short and factual. |

**When to change temperature:**
> For this agent, temperature should *always* stay at 0.0. If the user requests creative analysis ("What's a fun fact about AAPL?"), either reject it (out of scope) or refuse to answer. Do NOT increase temperature for any query.

### 4b. Prompt Architecture

**System Prompt Role:** Establishes agent identity, guardrails, output format preferences, and data source context.

```
You are a Financial Data Analyst — a precise, data-driven agent that retrieves 
stock market information from Yahoo Finance and delivers clear, factual insights 
to financial advisors.

## Core Responsibilities
1. Retrieve accurate financial data (price, P/E, EPS, market cap, ranges) from Yahoo Finance
2. Analyze trends and patterns without speculation
3. Format output as clear markdown (tables + narrative mix)
4. Include data timestamp and source (Yahoo Finance)
5. Refuse investment recommendations gracefully

## Guardrails (Non-negotiable)
- DO NOT provide buy/sell recommendations
- DO NOT cover crypto, forex, derivatives, or private companies
- DO NOT speculate or editorialize
- DO provide self-help steps when you cannot answer

## When You Cannot Answer
1. Explain WHY (invalid ticker, missing data, out of scope)
2. Suggest NEXT STEPS (how user can verify ticker, check YFinance directly, etc.)
3. Offer to help with valid queries

## Output Format
- Use markdown tables for multi-stock comparisons
- Use narrative + bullet points for analysis
- Always include: timestamp of data pull, source (Yahoo Finance)
- NO JSON. Markdown only.

## Data Accuracy
Source all numbers directly from YFinance tool output. If a field is missing or 
invalid, note it as "N/A" and continue. Do not estimate or infer values.
```

**User Prompt Role:** Receives the advisor's query, embedded with context; LLM processes and routes to tool or refusal.

```
Advisor Query: {user_query}

Current Timestamp: {current_timestamp}
Available Tools: YFinanceTools (stock price, fundamentals, ratios)

Analyze the query:
1. Extract ticker symbol(s) — if ambiguous, ask the user to clarify
2. Identify scope: quick lookup (price only) or deep dive (full fundamentals + analysis)?
3. Check guardrails: Is this a buy/sell recommendation? Crypto? Derivatives? → If yes, refuse politely
4. If safe: call YFinanceTools with tickers → parse results → format response
5. If data missing: explain gap + suggest self-help steps
6. Return single-shot, complete response in markdown

Go.
```

**Critical constraint:** 
> The system prompt's guardrails section must be included verbatim in every call. The phrase "DO NOT provide buy/sell recommendations" is non-negotiable — it prevents the agent from crossing into regulated territory. If the LLM omits this during fine-tuning or prompt injection, output quality degrades.

### 4c. Memory Configuration

| Memory Type | Used? | Notes |
|---|---|---|
| In-context (conversation history) | No | Single-shot interaction. Each query is independent; no follow-ups expected. |
| Vector / RAG | No | YFinance API is the sole source; no need for document retrieval. |
| External DB | No | No session state, user profiles, or query history storage in v1. |
| Session state | No | Stateless design. Same query from different users produces same response. |

**Upgrade path:** 
> Multi-turn support (Level 2) would add session-scoped memory: "Tell me more about MSFT's margins" could reference the previous MSFT response without re-fetching. This would require wrapping the agent in a conversation manager.

### 4d. Tools Configuration

| Tool | Used? | Notes |
|---|---|---|
| YFinanceTools (all functions) | Yes (full) | Fetches: price, % change, P/E, EPS, market cap, 52-week range, dividend yield, etc. All fields available; agent uses what's relevant to the query. |
| Web search | No | YFinance is live data; web search unnecessary and risks outdated or conflicting information. |
| External news API | No | Out of scope in v1. Advisor's workflow is data lookup, not news synthesis. |
| Sentiment analysis | No | NLP model overhead not justified for this use case. |

**Upgrade path:** 
> Adding a sentiment/news API (e.g., NewsAPI) would allow queries like "What's market sentiment on NVDA?" This would require Level 3 (ReAct loop) to reason about whether to fetch news alongside price data.

---

## Section 5 — Data Flow & Security Notes

- **OpenRouter API Key:** Stored as environment variable (e.g., `OPENROUTER_API_KEY`). Risk: if hardcoded in script, exposed in git history. Mitigation: use `.env` file + `.gitignore`, document in runbook.

- **User Data Sent to External Services:** 
  - Query text is sent to OpenRouter → Claude LLM (plain text, no PII expected).
  - Ticker symbols are sent to YFinance API (no PII).
  - Advisor names, portfolio data: NOT sent anywhere. This is a read-only lookup tool.

- **Data Written to Disk:** 
  - Jupyter notebook outputs: cached in cell outputs (local only).
  - Optional: CSV export of results (user action, not automatic).
  - Logs: debug logs may be printed to console; consider rotating to file in production.

- **Third-party Data Retention:** 
  - OpenRouter: see their privacy policy. Query text may be retained briefly for abuse detection.
  - YFinance: query access is read-only; no user data stored. Standard market data vendor terms.

---

## Section 6 — Data Grounding & Freshness

| Dimension | Detail |
|---|---|
| Data source | Yahoo Finance API (via YFinanceTools) — live market data feed |
| Knowledge cutoff | Not applicable. This is live data, not LLM training knowledge. |
| Grounding method | Direct API calls to YFinance; no RAG, no web search, no cached training data. |
| Freshness risk | **Low.** Market data refreshes on market hours (~15–20 min delay typical). Data is always current within the standard market feed delay. |
| Mitigation | Agent includes data pull timestamp in every response. Advisor can verify on live Yahoo Finance if real-time confirmation needed. Set user expectations: "This data is ~15 min delayed, as standard for Yahoo Finance." |
| Upgrade path | Subscribe to premium market data (Bloomberg, FactSet, Refinitiv) for intraday or real-time. Swap YFinanceTools for premium vendor APIs. |

---

## Section 7 — Eval Success Definition (Pre-Build)

| Criterion | What "good" looks like |
|---|---|
| **Data Accuracy** | Agent response matches Yahoo Finance source exactly (price, P/E, market cap, etc.). Spot-check 5 queries; 100% match required. |
| **Guardrail Adherence** | When user asks "Should I buy AAPL?" agent refuses politely and reframes data without advice. No hedging ("This isn't advice, but..."). Clear refusal boundary. |
| **Edge Case Handling** | Invalid ticker → explains error + suggests how to verify on Yahoo Finance. Missing P/E → notes "N/A", continues with available data. Crypto request → declines + explains YFinance limitation. |
| **Output Clarity** | Advisor can immediately extract 2–3 key metrics from response. Tables are readable, narrative is concise (< 150 words for deep dives). |
| **Latency** | Response generated in < 5 seconds (OpenRouter call + YFinance API + formatting). No hangs or timeouts. |
| **Self-Help Quality** | When agent cannot answer, user can follow provided steps to find answer independently (e.g., "Go to Yahoo Finance, search 'ticker name', check Valuation tab"). Steps are unambiguous. |

**Minimum bar for v1:** 
> Agent must: (1) accurately retrieve and return YFinance data without errors, (2) refuse buy/sell recommendations, and (3) handle invalid tickers gracefully. If any of these fail, the agent is not production-ready.

---

## Quality Checklist

- [x] Architecture Decision explicitly names Level 1 and explains why higher levels are overkill
- [x] Workflow diagram is complete: input → LLM processing → tool call → output
- [x] All model parameters have rationale (temperature locked at 0.0, Haiku for cost, 2000 tokens for scope)
- [x] System prompt explicitly encodes guardrails (buy/sell refusal, no crypto, etc.)
- [x] Eval success is specific: "100% match to YFinance", "graceful refusal", "< 5 seconds latency"
- [x] Data grounding is honest: Low freshness risk because YFinance updates regularly
- [x] No code in this document — only design intent and architecture

---

**Next step:** Proceed to Phase 3 (Build & Code) once this design is approved. The Code phase will translate this architecture into Python using OpenRouter SDK + YFinanceTools.
