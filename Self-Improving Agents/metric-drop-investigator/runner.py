"""Build the Agno agent from the current configuration and run it, logging everything.

Used by both the dashboard and the CLI (agent.py).
"""
import json
import os
import time
from datetime import datetime, timezone

os.environ.setdefault("AGNO_TELEMETRY", "false")  # no usage data leaves the app unless you opt in

from agno.agent import Agent

import config
import llm
import memory
import tools
from db import connect


def build_instructions(cfg: dict) -> tuple[str, int]:
    """Active system prompt + memory section. Returns (text, prompt_version_id)."""
    p = config.active_prompt()
    text = p["text"].replace("{causes}", config.causes_block(cfg))
    mode = cfg["memory_mode"]
    if mode == "tool":
        text += "\n\nMemory\nCall recall_memory FIRST. Past lessons and graded outcomes tell you which causes were real before and which mistakes you made. Obey them."
    elif mode == "inject":
        text += "\n\nMemory (already loaded for you; obey it)\n" + memory.memory_block(int(cfg["memory_max_lessons"]))
    return text, p["id"]


def build_agent(cfg: dict | None = None, model=None, api_key: str | None = None,
                provider: str | None = None) -> tuple[Agent, int]:
    cfg = cfg or config.load()
    instructions, version = build_instructions(cfg)
    model = model or llm.get_model(provider or cfg["provider"], cfg["model"] or None, api_key, cfg["base_url"] or None)
    agent = Agent(
        name="Metric Anomaly Investigator",
        model=model,
        tools=tools.build_tools(cfg),
        instructions=instructions,
        tool_call_limit=int(cfg["tool_call_limit"]),   # hard ceiling on the investigation loop
        add_datetime_to_context=True,
        markdown=True,
    )
    return agent, version


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_agent(task: str | None = None, api_key: str | None = None, model=None,
              provider: str | None = None) -> dict:
    """Run one investigation. Always logs a row in `runs`, even on failure."""
    cfg = config.load()
    task = task or cfg["default_task"]
    con = connect()
    cur = con.execute("INSERT INTO runs(ts,task,status) VALUES (?,?,'running')", (_now(), task))
    run_id = cur.lastrowid
    con.commit()
    tools.RUN["id"] = run_id
    started = time.time()
    result = {"run_id": run_id, "status": "error", "answer": "", "steps": [], "error": None}
    try:
        agent, version = build_agent(cfg, model=model, api_key=api_key, provider=provider)
        resp = agent.run(task)
        steps = []
        for t in (resp.tools or []):
            steps.append({"tool": t.tool_name, "args": t.tool_args,
                          "result": str(t.result)[:4000], "error": bool(getattr(t, "tool_call_error", False))})
        m = resp.metrics
        result.update(status="ok", answer=str(resp.content or ""), steps=steps)
        con.execute(
            "UPDATE runs SET status='ok', provider=?, model=?, prompt_version=?, duration_s=?, tool_calls=?, "
            "input_tokens=?, output_tokens=?, answer=?, steps=? WHERE id=?",
            (llm.detect_provider(provider or cfg["provider"]), agent.model.id, version, time.time() - started, len(steps),
             getattr(m, "input_tokens", None), getattr(m, "output_tokens", None),
             result["answer"], json.dumps(steps), run_id))
    except Exception as e:                      # noqa: BLE001 - surface any failure in the dashboard
        result["error"] = f"{type(e).__name__}: {e}"
        con.execute("UPDATE runs SET status='error', duration_s=?, error=? WHERE id=?",
                    (time.time() - started, result["error"], run_id))
    finally:
        con.commit()
        tools.RUN["id"] = None
    return result
