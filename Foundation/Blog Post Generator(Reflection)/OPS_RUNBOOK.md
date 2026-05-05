# Ops Runbook — Blog Post Generator Agent
> Phase 5: Operate | Project: Blog Post Generator Agent
> Run Environment: Python script / Jupyter Notebook (local)
> Status: Complete

---

## Section 1 — Security Checklist

### Critical — Do Before Pushing to GitHub

| Check | Status | Notes |
|---|---|---|
| API key is NOT hardcoded in the script | ☐ | See fix below — currently a commented `os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."` line is in the script |
| `.env` file is in `.gitignore` | ☐ | Create `.gitignore` and add `.env` as first entry |
| Jupyter notebook outputs are cleared before commit | ☐ | Draft/critique/revised text is printed to cell output — clear all outputs via Kernel → Restart & Clear Output |
| `.ipynb` checkpoint files excluded | ☐ | Add `.ipynb_checkpoints/` to `.gitignore` |
| Anthropic API spend limit set | ☐ | Go to console.anthropic.com → Billing → Set monthly soft limit to $10 and hard limit to $20 |
| No personal data in topic/audience strings | ☐ | If you've tested with real company names or product details, sanitise before committing |

**API key fix — apply immediately:**

```python
# ❌ Current (insecure — never commit this)
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

# ✅ Fix: use python-dotenv
# 1. pip install python-dotenv
# 2. Create .env file: ANTHROPIC_API_KEY=sk-ant-...
# 3. Add to script:
from dotenv import load_dotenv
load_dotenv()
client = anthropic.Anthropic()  # auto-reads from environment
```

---

## Section 2 — Prompt Injection Risk Assessment

**Overall risk level: Low**

This agent accepts `topic` and `audience` as inputs set by the developer in code — not as free-form user input from an untrusted source. There is no web interface, no user-facing form, and no runtime input collection in v1.

| Scenario | Risk level | Mitigation |
|---|---|---|
| Developer accidentally injects a jailbreak via topic string | Low | Inputs are set in code by the developer themselves — no external attack surface |
| Critic system prompt is overridden by crafted draft content | Low | The critic prompt wraps the draft in a clearly-labelled "Draft:" section; model boundaries are clear |
| If topic/audience become user-facing inputs in v2 | Medium | Sanitise inputs: strip `\n\n---\n`, `[SYSTEM]`, `Ignore all previous instructions` patterns; cap input length at 200 characters |
| Revised output contains harmful content due to adversarial topic | Low | Topics are set by the developer; but if open to users, add a topic classification step before Call 1 |

---

## Section 3 — Cost Management

### Estimated Cost per Run (TC-01 — Happy Path)

| Call | Model | Input tokens (est.) | Output tokens (est.) | Cost per run (est.) |
|---|---|---|---|---|
| Call 1 — Producer | claude-sonnet-4-5 | ~150 | ~450 | ~$0.0027 |
| Call 2 — Critic | claude-sonnet-4-5 | ~650 | ~300 | ~$0.0029 |
| Call 3 — Reviser | claude-sonnet-4-5 | ~900 | ~450 | ~$0.0040 |
| **Total per run** | | ~1,700 | ~1,200 | **~$0.010** |

*Based on Anthropic claude-sonnet-4-5 pricing: $3/M input tokens, $15/M output tokens (verify current pricing at anthropic.com/pricing).*

At current pricing, **100 runs costs approximately $1.00.** Monthly cost for daily use: ~$0.30.

### Token Budget Controls

- **max_tokens = 600 (Producer/Reviser):** Limits output to ~450 words. Increase to 900 if you want full 600-word articles.
- **max_tokens = 400 (Critic):** Known risk — complex topics may truncate critique. Increase to 600 (adds ~$0.003/run) based on TC-03 eval results.
- **Cost optimisation:** Switch to `claude-haiku-4-5` for the Critic call. Critique quality degrades slightly but cost drops ~80% for that call. Test on TC-01 before committing.

---

## Section 4 — Observability

### What you would log in production

| Event | What to Log | Why |
|---|---|---|
| Call 1 completion | timestamp, topic, audience, input_tokens, output_tokens, latency_ms | Track cost per topic; identify slow calls |
| Call 2 completion | timestamp, critique_length_words, input_tokens, output_tokens, latency_ms | Detect truncation (critique < 150 words = likely cut off) |
| Call 3 completion | timestamp, draft_word_count, revised_word_count, delta_words, latency_ms | Track whether revision is substantive (delta < 20 words = likely paraphrase failure) |
| API error | timestamp, call_number, error_type, topic | Surface rate limits and auth failures |

### What you can log right now (zero infrastructure)

Add this wrapper to your script for immediate timing and token visibility:

```python
import time

def timed_call(label, fn, *args):
    start = time.time()
    result = fn(*args)
    elapsed = round((time.time() - start) * 1000)
    # Access usage from the raw response object
    print(f"[{label}] {elapsed}ms | tokens: in={result.usage.input_tokens} out={result.usage.output_tokens}")
    return result.content[0].text

# Replace direct calls:
draft    = timed_call("PRODUCER", lambda t, a: client.messages.create(...), topic, audience)
critique = timed_call("CRITIC",   lambda d, a: client.messages.create(...), draft, audience)
revised  = timed_call("REVISER",  lambda d, c: client.messages.create(...), draft, critique)
```

---

## Section 5 — Known Limitations & Error Handling

| Limitation | Current behaviour | Better behaviour |
|---|---|---|
| No API key → AttributeError or AuthenticationError | Script crashes with an opaque SDK error | Check `os.environ.get("ANTHROPIC_API_KEY")` at startup; print "Set ANTHROPIC_API_KEY before running" and exit cleanly |
| API timeout or rate limit | Unhandled exception; script halts mid-run | Wrap each call in try/except; on rate limit, wait 60s and retry once; log the error |
| Critique truncated by max_tokens | Critique ends mid-sentence; dimensions 4–5 missing | Detect truncation: if `stop_reason == "max_tokens"`, warn user and suggest increasing limit |
| Vague inputs produce vague critique | Critique is generic ("improve the hook"); revision makes minimal changes | Add input validation: warn if topic < 5 words or audience < 3 words |
| Revised draft nearly identical to draft | No error; just poor output | Add a similarity check: count shared n-grams; if overlap > 70%, warn "Revision may not be substantive — consider strengthening critique prompt" |
| No error on empty string inputs | Claude generates content about an empty topic ("Write a blog about: ") | Add `assert topic.strip() and audience.strip(), "topic and audience cannot be empty"` |

---

## Section 6 — Feedback Loop

How to improve this agent over time as a solo PM:

1. **After each run:** Read the critique and the revised draft side-by-side. Ask: did the revision actually address the critique's numbered points? If not, that's the reviser prompt failing — log the gap in `PROMPT_LOG.md`.

2. **After 5 runs:** Look for patterns in the critique. If "vague examples" appears in 4/5 critiques, the producer prompt needs a stronger instruction to use concrete examples — fix it at the source, not the revision stage.

3. **Iterate one prompt at a time:** Change one prompt element per iteration. Run all 5 TC test cases before and after. If you change the critic prompt and the reviser prompt in the same run, you can't isolate what moved the score.

4. **Compare versions:** Keep a copy of the previous prompt version. Run TC-01 on both and compare draft quality and revision improvement scores. A prompt change is only a win if it improves ≥ 2 test cases without regressing any.

---

## Section 7 — Upgrade Roadmap

| Upgrade | What it adds | Complexity | Priority |
|---|---|---|---|
| Web search tool injected before Call 1 | Grounds draft in current articles/stats; kills freshness risk | Low — add one tool call before generate_post() | High |
| Markdown file export for revised post | One-click publishable file; no manual copy-paste | Low — `open("output.md", "w").write(revised)` | High |
| Quality scoring as Call 4 with loop | Iterative refinement until score ≥ threshold; true reflection pattern | Medium — add loop control, exit condition, max iterations | Medium |
| Brand voice input (example posts) | Injects user's past writing style into producer system prompt | Medium — requires storing/retrieving example posts | Medium |
| Streamlit UI for non-technical users | Input fields for topic/audience; no code required to run | Medium — ~50 lines of Streamlit | Medium |
| Multi-format output (LinkedIn, Twitter thread, email) | One topic → multiple formats via routing pattern | High — redesign into Level 3 routing agent | Low |
| Topic freshness check via web search | Flags if the topic has been over-covered recently | Medium — add search + deduplication logic | Low |

---

## Section 8 — Next Level (First-Class Artifact)

> Informed by TC-05 (vague inputs stress test) and the "light paraphrase" failure mode from the Eval Scorecard.

**Architectural upgrade:** From Level 2 (Prompt Chain) → Level 3 (ReAct loop with quality scoring)

**One tool to add:** A 4th LLM call acting as a **Quality Scorer** — given the critique and the revised draft, it outputs a score (0–10) per dimension. If average < 7, the loop re-runs the reviser with the score attached ("Your previous revision scored 4/10 on actionability — focus your next rewrite on this").

**The eval that currently fails that this fixes:** TC-05 stress test — vague topic/audience produces a light paraphrase in the revised draft. A quality scorer catches the low actionability score and forces another revision pass.

**What this teaches for the next project:** Adding a numeric gate to a prompt chain is the exact mental model shift from "sequential execution" to "iterative agent" — the LLM's output now influences whether the loop continues or exits.

| Upgrade | Fixes | New complexity introduced |
|---|---|---|
| Quality scorer + revision loop | "Light paraphrase" failure; vague critique failure in TC-05 | Loop exit conditions; max_iterations guard; token cost multiplies per iteration |
| Web search injection | Freshness risk; generic draft content; stale statistics | Tool call error handling; search result parsing; context window grows with injected articles |
| Brand voice retrieval | Tone mismatch for niche audiences (TC-04) | Storage of example posts; retrieval logic; prompt length management |

---

## Section 9 — Threat Model

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| API key committed to GitHub via notebook cell output or hardcoded assignment | High — common beginner mistake, and the current code has a commented insecure example | High — key can be scraped by bots within minutes; leads to unexpected API bills | Use python-dotenv; clear notebook outputs before commit; add pre-commit hook that scans for `sk-ant-` patterns |
| Runaway API spend from looped testing without token tracking | Medium — developer runs script 200x during prompt iteration without monitoring | Medium — $20–50 unexpected charge before hitting hard limit | Set Anthropic hard spend limit; add cumulative token counter to script output |
| Generated blog content contains factually incorrect claims (LLM hallucination) | Medium — concept-driven posts are lower risk; stat-heavy posts are higher risk | Medium — reputational risk if published without review | Document in README: "Always fact-check statistics and named claims before publishing"; add a disclaimer to printed output |
| Audience-specific content inadvertently reinforces cultural stereotypes | Low — "senior PMs at Indian tech companies" is a professional audience, not a demographic target | Medium — if published, could harm the writer's professional reputation | Review revised output for generalizations before publishing; add a "review for bias" checkpoint to the feedback loop |
| Dependency vulnerability in `anthropic` SDK | Low — SDK is actively maintained; attack surface is minimal for a local script | Low — primarily a local development tool with no internet-exposed endpoints | Pin SDK version in `requirements.txt`; run `pip audit` before any production deployment |
