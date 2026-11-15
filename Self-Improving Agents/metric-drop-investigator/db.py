"""SQLite schema + helpers shared by ingestion, tools, runner, and the dashboard."""
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
# Set DATA_DIR to a persistent disk when deploying; otherwise ./data
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "crates.db"

# Default crates to track (editable in the dashboard).
WATCHLIST = [
    "serde", "tokio", "rand", "clap", "syn", "regex",
    "anyhow", "libc", "hyper", "reqwest", "itertools", "log",
]

# Default cause taxonomy (editable in the dashboard).
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

-- One row per agent execution (monitoring).
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    task TEXT NOT NULL,
    provider TEXT, model TEXT,
    prompt_version INTEGER,
    status TEXT NOT NULL,              -- ok | error
    duration_s REAL,
    tool_calls INTEGER,
    input_tokens INTEGER, output_tokens INTEGER,
    answer TEXT,
    steps TEXT,                        -- JSON list of tool calls
    error TEXT
);

-- Agent memory: every investigation, later graded by a human.
CREATE TABLE IF NOT EXISTS investigations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    crate TEXT NOT NULL,
    event_date TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    confidence TEXT,
    evidence TEXT,
    steps TEXT,
    status TEXT NOT NULL DEFAULT 'pending',   -- pending | confirmed | corrected
    true_cause TEXT,
    feedback_note TEXT,
    graded_at TEXT,
    run_id INTEGER
);

-- Distilled, reusable lessons the agent reads.
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    situation TEXT NOT NULL,
    lesson TEXT NOT NULL,
    source TEXT NOT NULL               -- 'agent' | 'feedback' | 'manual'
);

-- Versioned system prompts so changes can be compared and rolled back.
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    label TEXT NOT NULL,
    text TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 0
);
"""


def _migrate(con: sqlite3.Connection) -> None:
    """Add columns to databases created by earlier versions."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(investigations)")}
    for name, ddl in (("graded_at", "TEXT"), ("run_id", "INTEGER")):
        if name not in cols:
            con.execute(f"ALTER TABLE investigations ADD COLUMN {name} {ddl}")
    con.commit()


def connect(readonly: bool = False) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists() or not readonly:
        con = sqlite3.connect(DB_PATH)
        con.executescript(SCHEMA)
        _migrate(con)
        if not readonly:
            con.row_factory = sqlite3.Row
            return con
        con.close()
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con
