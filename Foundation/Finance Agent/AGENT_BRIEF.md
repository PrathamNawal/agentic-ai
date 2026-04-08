# Agent Brief: YFinance Market Research Agent
**Phase 1 — Define**

---

## Section 1 — Problem Statement

Financial advisors spend significant time manually searching Yahoo Finance for stock data, switching between tabs, and compiling metrics across multiple stocks to build investment theses. This context-switching delays analysis and increases the risk of data entry errors. Advisors need a fast, accurate way to retrieve comparable financial data across one or many stocks without leaving their workflow.

**This agent solves:** Instantly retrieve accurate financial data from Yahoo Finance for single or multiple stocks, surfaced as clear analysis with tables and narratives — enabling advisors to focus on insight, not data gathering.

---

## Section 2 — User Persona

| Field | Detail |
|---|---|
| Name | Financial Advisor / Investment Analyst |
| Who | Wealth managers, portfolio advisors, or equity research analysts who advise clients on investment decisions |
| Context | Mid-analysis: advisor has identified 1–5 tickers of interest and needs to pull current fundamentals (P/E, market cap, 52-week range, EPS, price, % change) to frame a thesis |
| Tech comfort | Moderate to high — comfortable with tools, CLI, or API, but prefers talking to typing |
| Goal | Get accurate, fresh financial data in under 30 seconds with no manual lookup required |
| Frustration | Manually searching Yahoo Finance for each metric, copying/pasting into spreadsheets, risk of stale or mismatched data across stocks |

---

## Section 2a — Job-to-be-Done (JTBD)

> **When I** am building an investment thesis and need to compare 2–5 stocks on key metrics, **I want to** ask the agent once and get clean, accurate data with brief analysis, **so I can** spend my time on judgment and strategy, not data entry.

---

## Section 3 — Input / Output Specification

**Inputs:**

| Input | Type | Example | Required |
|---|---|---|---|
| Query | string | "Compare MSFT, GOOGL, and AMZN on P/E, revenue growth, and margins" | Yes |
| Stock ticker(s) | string (single or comma-separated) | "AAPL" or "NVDA, AMD, MSFT" | Embedded in query |
| Analysis depth | implicit enum | "What's AAPL trading at?" (quick) vs. "Break down MSFT's financials" (deep) | No — agent infers from query |

**Outputs:**

| Output | Format | Description |
|---|---|---|
| Market data | Markdown table or narrative | Current price, % change, P/E, EPS, market cap, 52-week range, and any requested metrics |
| Analysis | Mixed narrative + table | Key drivers, sector context, data quality notes, timestamp of data pull |
| Disclaimer | Text (conditional) | Data source (Yahoo Finance) and timestamp; appears only if necessary for context |
| Self-help steps | Text (conditional) | If agent can't answer, explicit steps for user to retrieve data independently |

---

## Section 4 — Step-by-Step Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    YFINANCE MARKET RESEARCH AGENT WORKFLOW                  │
└─────────────────────────────────────────────────────────────────────────────┘

                                ┌──────────────┐
                                │   Advisor    │
                                │   Submits    │
                                │   Query      │
                                └──────┬───────┘
                                       │
                   ┌───────────────────▼───────────────────┐
                   │  Parse Query                          │
                   │  • Extract ticker(s)                  │
                   │  • Identify scope                     │
                   │  • Clarify ambiguity                  │
                   └───────────────────┬───────────────────┘
                                       │
                   ┌───────────────────▼───────────────────┐
                   │  Guardrail Check                      │
                   │  • Buy/sell recommendation? ──────┐   │
                   │  • Crypto/forex/derivatives? ──┐  │   │
                   │  • Valid ticker exists? ────┐  │  │   │
                   └───────────────────┬─────┬─┬─┬┘───┘   │
                                       │     │ │ └─────────┐
                         ┌─────────────┘     │ │           │
                         │                   │ │           │
                    ┌────▼─────────────┐  ┌──▼─▼───┐  ┌────▼──────────┐
                    │ Fetch Data       │  │Refuse  │  │  Edge Case    │
                    │ via YFinance     │  │Polite- │  │ • Invalid     │
                    │ • Price          │  │ly +    │  │ • Missing     │
                    │ • P/E, EPS       │  │Reframe │  │   data        │
                    │ • Market cap     │  └────┬───┘  │ Explain +     │
                    │ • 52-week range  │       │       │ Self-help     │
                    │ • % change       │       │       │ steps         │
                    └────┬─────────────┘       │       └────┬──────────┘
                         │                     │            │
                    ┌────▼─────────────────────▼────────────▼────┐
                    │  Analyze Data                               │
                    │  • Compute ratios (if needed)               │
                    │  • Identify trends & drivers                │
                    │  • Add sector context                       │
                    └────┬────────────────────────────────────────┘
                         │
                    ┌────▼────────────────────────────┐
                    │  Format Response                │
                    │  Agent decides best format:     │
                    │  • Quick query → Concise text   │
                    │  • Comparison → Tables + brief  │
                    │  • Deep dive → Mixed narrative  │
                    └────┬────────────────────────────┘
                         │
                    ┌────▼──────────────────────┐
                    │  Add Metadata              │
                    │  • Timestamp (data pull)   │
                    │  • Data source (YFinance)  │
                    │  • Disclaimer (if needed)  │
                    └────┬──────────────────────┘
                         │
                    ┌────▼──────────────────────┐
                    │  Return Response          │
                    │  (single-shot, complete)  │
                    └────┬──────────────────────┘
                         │
                         ▼
                    ┌──────────────┐
                    │   Advisor    │
                    │   Receives   │
                    │   Analysis   │
                    └──────────────┘
```

**Key Decision Points:**
- **Guardrail Check**: Routes to refusal (with reframe) or edge case (with self-help) if conditions aren't met
- **Format Choice**: Agent intelligently selects presentation based on query type
- **Single-shot delivery**: Response is complete and requires no follow-up

---

## Section 5 — Success Metrics

| Metric | Target | How to Measure |
|---|---|---|
| Data accuracy | 100% match to Yahoo Finance source | Spot-check sample queries; compare agent output to live Yahoo Finance |
| Response latency | < 5 seconds for most queries | Time from query submission to response delivery |
| Query scope handling | Correctly parse 1–5 tickers and interpret depth (quick vs. deep) | Test suite covering quick lookups, comparisons, and deep dives |
| Refusal quality | Graceful decline on buy/sell recommendations + actionable self-help | User perceives the refusal as helpful, not as a brick wall |
| Self-help clarity | Clear, step-by-step next steps when agent cannot answer | Advisor can execute steps independently without follow-up |

---

## Section 6 — Constraints & Assumptions

**Constraints:**
- Data source is Yahoo Finance only — no alternative data providers, no crypto, forex, derivatives, or private equities.
- Single-shot interaction — no multi-turn conversations or follow-up refinements.
- No real-time streaming; data may be delayed by minutes (as per Yahoo Finance standard).
- Cannot provide investment recommendations, financial advice, or client-specific portfolio analysis.
- No access to insider trading data, earnings call transcripts, or proprietary research.

**Assumptions:**
- User has a valid stock ticker symbol (or agent can infer it from a company name).
- Yahoo Finance API is available and responsive (no extended outages).
- User is a financial professional with baseline knowledge of equity metrics (P/E, EPS, market cap).
- User accepts the Yahoo Finance data delay and timestamp convention.
- User will not attempt to use the agent for crypto, commodities, or options.

---

## Section 7 — Contra-Indicators (When NOT to Use This Agent)

| Situation | Why it's unfit | Better alternative |
|---|---|---|
| Real-time intraday trading | Yahoo Finance data lags; unsuitable for high-frequency decisions | Interactive brokers' APIs, Bloomberg Terminal, or market data vendors |
| Private equity / M&A analysis | YFinance has no coverage of private companies | Crunchbase, PitchBook, manual research |
| Cryptocurrency or derivatives | YFinance limited to public equities | CoinGecko, Deribit, or specialized crypto platforms |
| Sector-wide macro analysis (>5 tickers) | Agent excels at 1–5; large universes become unwieldy | Index dashboards, sector ETF tracking, or third-party analysis platforms |
| Personalized portfolio advice | Agent explicitly refuses recommendations | Fiduciary advisors, robo-advisors (Vanguard, Wealthfront), or human financial planners |
| ESG/sustainability screening | Yahoo Finance limited ESG data coverage | Refinitiv, MSCI, or specialized ESG platforms |

---

## Section 8 — Data Grounding & Freshness

| Dimension | Detail |
|---|---|
| Data source | Yahoo Finance (via YFinanceTools) |
| Knowledge cutoff | Not applicable — Yahoo Finance returns live market data, not LLM knowledge |
| Grounding method | Direct API calls to Yahoo Finance; no RAG or web search involved |
| Freshness risk | Low – Market data refreshes automatically; typically 15–20 min delay (standard market feed) |
| Mitigation | Agent timestamps all responses; user can verify on live Yahoo Finance if real-time confirmation needed |
| Upgrade path | Integrate Bloomberg Terminal, FactSet, or premium market data providers for intraday / real-time data |

---

## Section 9 — Top 3 Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Yahoo Finance API downtime or rate limiting | Medium | High | Implement retry logic with exponential backoff; alert user to outage; provide fallback link to Yahoo Finance |
| User requests buy/sell recommendation (guardrail breach) | High | Medium | Pre-emptive instruction in system prompt with refusal template + reframe-for-advisor pattern; log refusals for feedback loops |
| Ticker symbol ambiguity or user typo (e.g., "APPL" vs "AAPL") | Medium | Medium | Agent asks clarifying question on first fail; provides top 3 suggestions; links to Yahoo Finance search for user to verify |

---

## Section 10 — Learning Objectives (PM Lens)

- **Prompt engineering concept**: Explicit guardrails and refusal templates — this agent demonstrates how to encode "what the agent must NOT do" as clearly as "what it should do."
- **LLM parameter**: Temperature near 0 (deterministic output) — financial data demands precision, not creativity.
- **Architectural insight**: This is a **tool-use pattern** (agent + single external tool), not a prompt chain. The agent's job is interpretation and formatting, not orchestration of complex sequences.
- **Natural upgrade path**: Add multi-turn support to allow follow-up queries ("Tell me more about margins") without re-fetching data; or integrate sentiment analysis via news APIs to add advisor context.

---

> **Key insight for this project:** Effective agent guardrails aren't about saying "no" — they're about transparent refusal + actionable next steps. Advisors trust the agent more when it explains *why* it can't answer and *how* they can find the answer themselves.

---

## Readiness Checklist

- [x] Problem statement is specific to financial advisors and Yahoo Finance
- [x] User persona includes tech comfort, context, and frustration
- [x] JTBD follows exact "When I / I want to / so I can" format
- [x] Contra-indicators table has 6 rows with specific alternatives
- [x] Top 3 risks ranked by priority (user requests, data freshness, ticker ambiguity)
- [x] No code or implementation detail in the brief
- [x] Brief is readable by non-technical stakeholders (CFO, product manager)

---

**Next step:** Proceed to Phase 2 (Design Doc) once this brief is approved.
