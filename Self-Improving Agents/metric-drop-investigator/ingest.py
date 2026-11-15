"""Ingest REAL daily download data + release history from the crates.io API.

crates.io only exposes the last ~90 days of daily downloads per crate, so this
script is meant to be re-run (cron / loop). Upserts are idempotent and history
accumulates beyond 90 days the longer you run it.

    python ingest.py                 # whole watchlist
    python ingest.py serde tokio     # specific crates
    python ingest.py --loop 6        # re-ingest every 6 hours
    python ingest.py --export        # also write CSV snapshots to data/snapshots/
"""
import argparse
import csv
import time
from datetime import datetime, timezone

import requests

import config
from db import DB_PATH, ROOT, connect

API = "https://crates.io/api/v1"
# crates.io asks API clients to identify themselves and stay under 1 req/sec.
HEADERS = {"User-Agent": "metric-drop-investigator (open-source research agent)"}
PAUSE = 1.1


def get(path: str) -> dict:
    for attempt in range(4):
        r = requests.get(f"{API}{path}", headers=HEADERS, timeout=30)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** attempt * 2)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()


def ingest_crate(con, crate: str) -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    meta = get(f"/crates/{crate}")
    time.sleep(PAUSE)
    con.executemany(
        "INSERT OR REPLACE INTO versions VALUES (?,?,?,?,?,?)",
        [
            (v["id"], crate, v["num"], v["created_at"], int(v["yanked"]), v.get("rust_version"))
            for v in meta["versions"]
        ],
    )

    dl = get(f"/crates/{crate}/downloads")
    time.sleep(PAUSE)
    rows = [(crate, d["date"], d["version"], d["downloads"], now) for d in dl["version_downloads"]]
    rows += [(crate, d["date"], 0, d["downloads"], now) for d in dl["meta"]["extra_downloads"]]
    con.executemany(
        "INSERT OR REPLACE INTO daily_downloads VALUES (?,?,?,?,?)", rows
    )
    con.execute("INSERT INTO ingest_runs VALUES (?,?,?)", (now, crate, len(rows)))
    con.commit()
    return len(rows)


def export_csv(con) -> None:
    out = ROOT / "data" / "snapshots"
    out.mkdir(parents=True, exist_ok=True)
    for table in ("versions", "daily_downloads"):
        cur = con.execute(f"SELECT * FROM {table} ORDER BY 1,2,3" if table == "daily_downloads" else f"SELECT * FROM {table} ORDER BY crate, created_at")
        with open(out / f"{table}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow([c[0] for c in cur.description])
            w.writerows(cur)
    print(f"exported CSV snapshots to {out}")


def load_snapshots(con) -> int:
    """Seed an empty database from the committed CSV snapshots (instant start, e.g. on a fresh deploy)."""
    snap = ROOT / "data" / "snapshots"
    if not (snap / "daily_downloads.csv").exists():
        return 0
    n = 0
    with open(snap / "versions.csv") as f:
        rows = [tuple(r.values()) for r in csv.DictReader(f)]
    con.executemany("INSERT OR IGNORE INTO versions VALUES (?,?,?,?,?,?)", rows)
    with open(snap / "daily_downloads.csv") as f:
        rows = [tuple(r.values()) for r in csv.DictReader(f)]
    con.executemany("INSERT OR IGNORE INTO daily_downloads VALUES (?,?,?,?,?)", rows)
    con.commit()
    return len(rows)


def ensure_data() -> bool:
    """True if the database has data (seeding it from snapshots on first start)."""
    con = connect()
    if con.execute("SELECT 1 FROM daily_downloads LIMIT 1").fetchone():
        return True
    return load_snapshots(con) > 0


def run(crates: list[str], export: bool) -> None:
    con = connect()
    for c in crates:
        try:
            n = ingest_crate(con, c)
            print(f"{c:10s} {n:4d} daily rows upserted")
        except Exception as e:  # keep going; one crate failing shouldn't stop the batch
            print(f"{c:10s} FAILED: {e}")
    total = con.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM daily_downloads").fetchone()
    print(f"db: {DB_PATH}  rows={total[0]} range={total[1]}..{total[2]}")
    if export:
        export_csv(con)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("crates", nargs="*", default=config.load()["watchlist"])
    ap.add_argument("--loop", type=float, metavar="HOURS", help="re-ingest forever, every N hours")
    ap.add_argument("--export", action="store_true", help="write CSV snapshots")
    a = ap.parse_args()
    while True:
        run(a.crates, a.export)
        if not a.loop:
            break
        time.sleep(a.loop * 3600)
