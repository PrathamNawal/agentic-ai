"""SQLite schema + helpers shared by ingestion, tools, runner, and the dashboard."""
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
# Set DATA_DIR to a persistent disk when deploying; otherwise ./data
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "complaints.db"

# Default cause taxonomy (editable in the dashboard, and the first thing a PM should sharpen).
CAUSES = {
    "EXTERNAL_EVENT": "A known outside event (regulation, data breach, news, policy change) explains it; cite the event.",
    "INDUSTRY_WIDE": "Many companies moved the same way on the same days; not specific to this company.",
    "MIX_SHIFT": "One product or issue drove the change while others were flat (look at the breakdown).",
    "CHANNEL_SHIFT": "The change comes from one submission channel (web, referral, phone...), e.g. a portal change or a campaign.",
    "BATCH_OR_CAMPAIGN": "A burst of near-identical complaints in a short window (coordinated filing, credit-repair batch).",
    "WEEKLY_SEASONALITY": "Normal weekday/weekend pattern; not a real anomaly.",
    "DATA_ARTIFACT": "Reporting lag, taxonomy rename, or incomplete recent days; not a real change in customer behaviour.",
    "UNEXPLAINED": "Evidence did not support any cause.",
}

SCHEMA = """
-- Daily complaint counts per company, overall ('total') and split by one dimension at a time:
-- product | issue | channel | response | timely.
CREATE TABLE IF NOT EXISTS daily_counts (
    entity TEXT NOT NULL,
    date TEXT NOT NULL,
    dimension TEXT NOT NULL,
    segment TEXT NOT NULL,
    count INTEGER NOT NULL,
    PRIMARY KEY (entity, date, dimension, segment)
);

-- Known events that can explain a move. entity '*' = applies to every company.
-- THIS is where a product manager contributes domain knowledge.
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity TEXT NOT NULL,
    date TEXT NOT NULL,
    title TEXT NOT NULL,
    kind TEXT,
    note TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);

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
    entity TEXT NOT NULL,
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
