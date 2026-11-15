"""Everything a product manager can tweak lives here (and is edited from the dashboard).

Settings are stored in data/config.json. System prompts are versioned in SQLite so
changes can be compared and rolled back.
"""
import json
from datetime import datetime, timezone

from db import CAUSES, DATA_DIR, WATCHLIST, connect

CONFIG_PATH = DATA_DIR / "config.json"

DEFAULT_PROMPT = """You are a senior data analyst investigating anomalies (drops AND surges) in daily
package downloads (crates.io, real data). You decide your own next step from what you
find: you are not following a fixed script.

Method
1. If no crate/date is given, call scan_for_anomalies and pick the most significant
   anomaly. crates_anomalous_per_date is a first hint for ECOSYSTEM_WIDE.
2. Form hypotheses, then test them with tools. Rule out cheap, common artifacts before
   concluding a real regression: weekday seasonality (the baseline is already
   same-weekday), partial days, ecosystem-wide moves (peer_comparison), a one-off spike
   in the baseline (daily_series), version shifts (version_breakdown + releases).
3. Stop when the evidence is decisive, or say UNEXPLAINED. Do not invent causes.
   Quote the concrete numbers that support your conclusion.
4. Call record_investigation exactly once with your conclusion. hypothesis must be one
   of these keys:
{causes}
5. If you learned something that would change how you investigate next time, call
   save_lesson (short, specific, actionable). Do not save trivia.

Rules
- Today's UTC date is always partial and is excluded from the data.
- Never claim a cause you did not test with a tool.
- Final answer: 3-6 lines: what moved, the cause, the key numbers, confidence."""

DEFAULTS = {
    # model (the API key is never stored here; it comes from env or the session)
    "provider": "auto",            # auto | openrouter | xai | groq | anthropic
    "model": "",                   # blank = provider default
    "base_url": "",                # optional OpenAI-compatible endpoint override
    # behaviour
    "tool_call_limit": 25,
    "default_task": "Scan the watchlist and investigate the most significant recent anomaly in daily downloads.",
    # analysis parameters used by the tools
    "anomaly_threshold_pct": 15.0,
    "baseline_weeks": 4,
    "scan_window_days": 30,
    # memory
    "memory_mode": "tool",         # tool = agent calls recall_memory | inject = lessons placed in prompt | off
    "memory_max_lessons": 15,
    # tools
    "disabled_tools": [],
    "tool_descriptions": {},       # per-tool description overrides
    "saved_queries": [],           # [{name, description, sql}] -> exposed via run_saved_query
    # domain
    "watchlist": WATCHLIST,
    "causes": CAUSES,
}


def load() -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save(cfg: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def update(**changes) -> dict:
    cfg = load()
    cfg.update(changes)
    save(cfg)
    return cfg


def reset() -> None:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()


def causes_block(cfg: dict) -> str:
    return "\n".join(f"   - {k}: {v}" for k, v in cfg["causes"].items())


# ------------------------------------------------------------ prompt versions
def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def list_prompts() -> list[dict]:
    con = connect()
    if not con.execute("SELECT 1 FROM prompt_versions LIMIT 1").fetchone():
        con.execute("INSERT INTO prompt_versions(ts,label,text,active) VALUES (?,?,?,1)",
                    (_now(), "Default", DEFAULT_PROMPT))
        con.commit()
    return [dict(r) for r in con.execute("SELECT * FROM prompt_versions ORDER BY id DESC")]


def active_prompt() -> dict:
    return next(p for p in list_prompts() if p["active"])


def save_prompt(text: str, label: str, activate: bool = True) -> int:
    list_prompts()  # make sure the default exists
    con = connect()
    if activate:
        con.execute("UPDATE prompt_versions SET active=0")
    cur = con.execute("INSERT INTO prompt_versions(ts,label,text,active) VALUES (?,?,?,?)",
                      (_now(), label or "Untitled", text, int(activate)))
    con.commit()
    return cur.lastrowid


def activate_prompt(prompt_id: int) -> None:
    con = connect()
    con.execute("UPDATE prompt_versions SET active=0")
    con.execute("UPDATE prompt_versions SET active=1 WHERE id=?", (prompt_id,))
    con.commit()
