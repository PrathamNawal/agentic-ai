"""SQLite schema + helpers shared by ingestion, tools, and feedback CLI."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "crates.db"

# Crates to track. Mix of ecosystem foundations and popular libraries so that
# "is this drop ecosystem-wide or specific to one crate?" is answerable.
WATCHLIST = [
    "serde", "tokio", "rand", "clap", "syn", "regex",
    "anyhow", "libc", "hyper", "reqwest", "itertools", "log",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS versions (
    id INTEGER PRIMARY KEY,
    crate TEXT NOT NULL,
    num TEXT NOT NULL,
    created_at TEXT NOT NULL,
    yanked INTEGER NOT NULL,
    rust_version TEXT
);
CREATE INDEX IF NOT EXISTS idx_versions_crate ON versions(crate, created_at);

-- version_id = 0 is the "other versions" bucket (crates.io only itemises the
-- top versions per day; the rest arrive as an aggregate).
CREATE TABLE IF NOT EXISTS daily_downloads (
    crate TEXT NOT NULL,
    date TEXT NOT NULL,
    version_id INTEGER NOT NULL,
    downloads INTEGER NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (crate, date, version_id)
);

CREATE TABLE IF NOT EXISTS ingest_runs (
    ts TEXT NOT NULL, crate TEXT NOT NULL, rows INTEGER NOT NULL
);

-- Agent memory: every investigation, later graded by a human.
CREATE TABLE IF NOT EXISTS investigations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    crate TEXT NOT NULL,
    event_date TEXT NOT NULL,
    hypothesis TEXT NOT NULL,          -- one of CAUSES
    confidence TEXT,
    evidence TEXT,
    steps TEXT,
    status TEXT NOT NULL DEFAULT 'pending',   -- pending | confirmed | corrected
    true_cause TEXT,
    feedback_note TEXT
);

-- Distilled, reusable lessons the agent reads before every run.
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    situation TEXT NOT NULL,
    lesson TEXT NOT NULL,
    source TEXT NOT NULL               -- 'agent' | 'feedback'
);
"""

CAUSES = {
    "VERSION_MIGRATION": "Traffic shifted between versions (new release / yank / dependency bump); total may be flat.",
    "ECOSYSTEM_WIDE": "Many peer crates moved the same way on the same day (up or down); not specific to this crate.",
    "WEEKLY_SEASONALITY": "Normal weekday/weekend pattern; not a real anomaly.",
    "TRANSIENT_SPIKE_REVERSION": "A one-off spike in the baseline made a normal day look like a drop.",
    "CI_OR_BOT_SURGE": "A surge confined to one crate or one version (CI storm, mirror, bot), not organic growth.",
    "PARTIAL_OR_MISSING_DATA": "Day is incomplete or data is missing; not a real drop.",
    "RELEASE_REGRESSION": "A release coincides with a real, sustained decline for that crate.",
    "UNEXPLAINED": "Evidence did not support any cause.",
}


def connect(readonly: bool = False) -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    if readonly:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    else:
        con = sqlite3.connect(DB_PATH)
        con.executescript(SCHEMA)
    con.row_factory = sqlite3.Row
    return con
