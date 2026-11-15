"""Backup / restore everything the agent has learned and every setting, as one JSON file.

Free hosting tiers reset the disk on restart. Download a backup from the Memory page now and
then, and restore it after a restart so the agent keeps what it learned.
(Raw download data is not included: it is re-seeded or re-fetched from crates.io.)
"""
import json
from datetime import datetime, timezone

import config
from db import connect

TABLES = {
    "lessons": ["ts", "situation", "lesson", "source"],
    "investigations": ["ts", "crate", "event_date", "hypothesis", "confidence", "evidence", "steps",
                       "status", "true_cause", "feedback_note", "graded_at"],
    "prompt_versions": ["ts", "label", "text", "active"],
    "runs": ["ts", "task", "provider", "model", "prompt_version", "status", "duration_s", "tool_calls",
             "input_tokens", "output_tokens", "answer", "steps", "error"],
}


def export_json() -> str:
    config.list_prompts()  # make sure the default prompt row exists
    con = connect()
    out = {"exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "config": config.load()}
    for table, cols in TABLES.items():
        out[table] = [dict(r) for r in con.execute(f"SELECT {','.join(cols)} FROM {table} ORDER BY id")]
    return json.dumps(out, indent=2)


def import_json(raw: bytes | str) -> dict:
    """Replace the learned state with a backup. Returns row counts."""
    data = json.loads(raw)
    con = connect()
    counts = {}
    for table, cols in TABLES.items():
        con.execute(f"DELETE FROM {table}")
        rows = data.get(table, [])
        con.executemany(f"INSERT INTO {table}({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                        [tuple(r.get(c) for c in cols) for r in rows])
        counts[table] = len(rows)
    con.commit()
    if "config" in data:
        config.save(data["config"])
    return counts
