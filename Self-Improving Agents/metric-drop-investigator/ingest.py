"""Load the real CFPB complaints snapshot into SQLite (instant; no network needed).

The snapshot (data/snapshots/complaints_daily.csv.gz) is built once from the full public database by
build_dataset.py. On first start this module loads it and seeds a short list of starter events.

    python ingest.py          # (re)load the snapshot into an empty database
"""
import json
from datetime import datetime, timezone

import pandas as pd

from db import DB_PATH, ROOT, connect

SNAP = ROOT / "data" / "snapshots"

# Starter list from public knowledge so the agent has something to cite. NOT authoritative:
# the product manager should verify, edit, add, and delete events on the Data explorer page.
# `match` = substrings of company names the event applies to ('*' = all companies).
STARTER_EVENTS = [
    ("2020-03-13", "US declares COVID-19 national emergency", "macro", ["*"]),
    ("2020-03-27", "CARES Act signed (mortgage forbearance, student-loan payment pause)", "regulation", ["*"]),
    ("2022-07-01", "Credit bureaus stop reporting paid medical collections; 1-year wait before new ones",
     "policy", ["EQUIFAX", "EXPERIAN", "TRANSUNION"]),
    ("2023-04-11", "Credit bureaus remove medical collections under $500 from reports",
     "policy", ["EQUIFAX", "EXPERIAN", "TRANSUNION"]),
    ("2023-09-01", "Federal student-loan interest resumes after pandemic pause", "regulation", ["*"]),
    ("2023-10-01", "Federal student-loan payments resume", "regulation", ["*"]),
]
SOURCE = "starter list from public knowledge; verify before relying on it"


def load_snapshot(con) -> int:
    f = SNAP / "complaints_daily.csv.gz"
    if not f.exists():
        return 0
    df = pd.read_csv(f)
    con.executemany("INSERT OR REPLACE INTO daily_counts VALUES (?,?,?,?,?)",
                    df[["entity", "date", "dimension", "segment", "count"]].itertuples(index=False, name=None))
    meta = json.loads((SNAP / "dataset_meta.json").read_text()) if (SNAP / "dataset_meta.json").exists() else {}
    con.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)",
                    [(k, json.dumps(v)) for k, v in meta.items()])
    con.commit()
    return len(df)


def seed_events(con) -> int:
    if con.execute("SELECT 1 FROM events LIMIT 1").fetchone():
        return 0
    entities = [r[0] for r in con.execute("SELECT DISTINCT entity FROM daily_counts")]
    n = 0
    for date, title, kind, match in STARTER_EVENTS:
        targets = ["*"] if match == ["*"] else [e for e in entities if any(m in e.upper() for m in match)]
        for e in targets:
            con.execute("INSERT INTO events(entity,date,title,kind,note,source) VALUES (?,?,?,?,?,?)",
                        (e, date, title, kind, "", SOURCE))
            n += 1
    con.commit()
    return n


def ensure_data() -> bool:
    """True if the database has data (loading the snapshot on first start)."""
    con = connect()
    if not con.execute("SELECT 1 FROM daily_counts LIMIT 1").fetchone():
        if load_snapshot(con) == 0:
            return False
    seed_events(con)
    return True


def meta() -> dict:
    con = connect(readonly=True)
    return {r["key"]: json.loads(r["value"]) for r in con.execute("SELECT key,value FROM meta")}


if __name__ == "__main__":
    con = connect()
    print(f"loaded {load_snapshot(con):,} rows, seeded {seed_events(con)} events into {DB_PATH}")
