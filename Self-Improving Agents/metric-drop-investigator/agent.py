"""Metric Anomaly Investigator: a self-improving Agno agent over real crates.io data.

    export OPENROUTER_API_KEY=...   # or XAI_API_KEY / GROQ_API_KEY / ANTHROPIC_API_KEY (see llm.py)
    python agent.py                                   # scan watchlist, investigate the worst recent drop
    python agent.py "Why did tokio drop on 2026-11-03?"
"""
import sys

from agno.agent import Agent

from db import CAUSES
from llm import get_model
from tools import ALL_TOOLS

INSTRUCTIONS = f"""
You are a senior data analyst investigating anomalies (drops AND surges) in daily package downloads
(crates.io, real data). You decide your own next step from what you find: you
are not following a fixed script.

Method
1. Call recall_memory FIRST. Past lessons and graded outcomes tell you which
   causes were real before and which mistakes you made. Obey them.
2. If no crate/date is given, call scan_for_anomalies and pick the most significant
   anomaly. crates_anomalous_per_date is a first hint for ECOSYSTEM_WIDE.
3. Form hypotheses, then test them with tools. Rule out cheap, common artifacts
   before concluding a real regression: weekday seasonality (the baseline is
   already same-weekday), partial days, ecosystem-wide dips (peer_comparison),
   a one-off spike in the baseline (daily_series), version shifts
   (version_breakdown + releases).
4. Stop when the evidence is decisive, or say UNEXPLAINED. Do not invent causes.
   Quote the concrete numbers that support your conclusion.
5. Call record_investigation exactly once with your conclusion. hypothesis must
   be one of these keys:
{chr(10).join(f'   - {k}: {v}' for k, v in CAUSES.items())}
6. If you learned something that would change how you investigate next time,
   call save_lesson (short, specific, actionable). Do not save trivia.

Rules
- Today's UTC date is always partial and is excluded from the data.
- Never claim a cause you did not test with a tool.
- Final answer: 3-6 lines: what dropped, the cause, the key numbers, confidence.
"""


def build_agent(model=None) -> Agent:
    return Agent(
        name="Metric Anomaly Investigator",
        model=model or get_model(),
        tools=ALL_TOOLS,
        instructions=INSTRUCTIONS,
        tool_call_limit=25,   # hard ceiling on the investigation loop
        add_datetime_to_context=True,
        markdown=True,
    )


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "Scan the watchlist and investigate the most significant recent anomaly in daily downloads."
    build_agent().print_response(task, stream=True)
