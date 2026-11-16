"""Metric Anomaly Investigator CLI. (The dashboard, `streamlit run app.py`, is the easy way.)

    export OPENROUTER_API_KEY=...   # or XAI_API_KEY / GROQ_API_KEY / ANTHROPIC_API_KEY (see llm.py)
    python agent.py                                   # scan all companies, investigate the biggest anomaly
    python agent.py "Why did complaints about Equifax spike on 2023-04-12?"

Prompt, tools, memory and thresholds come from config.py (edit them in the dashboard).
"""
import sys

from runner import build_agent, run_agent  # noqa: F401  (build_agent re-exported for scripts)

if __name__ == "__main__":
    out = run_agent(" ".join(sys.argv[1:]) or None)
    for s in out["steps"]:
        print(f"-> {s['tool']}({s['args']})")
    print("\n" + (out["answer"] or f"ERROR: {out['error']}"))
    sys.exit(0 if out["status"] == "ok" else 1)
