"""Tools the Agno agent can call. Every function returns a compact JSON string.

Analysis parameters (threshold, baseline weeks, scan window) come from config.py, so
a product manager can change them from the dashboard without touching code.

Assumptions:
- The metric is TOTAL daily downloads per crate (version rows + the 'other versions' bucket).
- Today (UTC) is always partial, so it is excluded from all anomaly logic.
- An anomaly is a day that deviates from the median of the same weekday over the previous
  N weeks, which removes weekly seasonality.
"""
import functools
import json
import re
import statistics as st
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import config
import memory
from db import connect

# The dashboard/runner sets this so investigations can be linked to their run.
RUN = {"id": None}


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _totals(con, crate: str) -> dict[str, int]:
    rows = con.execute(
        "SELECT date, SUM(downloads) t FROM daily_downloads WHERE crate=? AND date<? GROUP BY date",
        (crate, _today()),
    ).fetchall()
    return {r["date"]: r["t"] for r in rows}


def _baseline(totals: dict[str, int], d: str) -> float | None:
    """Median of the same weekday over the previous N weeks (needs >= min(3, N) points)."""
    weeks = int(config.load()["baseline_weeks"])
    dd = date.fromisoformat(d)
    pts = [totals[k] for w in range(1, weeks + 1)
           if (k := (dd - timedelta(weeks=w)).isoformat()) in totals]
    return st.median(pts) if len(pts) >= min(3, weeks) else None


def _out(obj) -> str:
    return json.dumps(obj, default=str)


# --------------------------------------------------------------- data tools
def list_crates() -> str:
    """List tracked crates with their data coverage (first/last complete date)."""
    con = connect(readonly=True)
    rows = con.execute(
        "SELECT crate, MIN(date) first_date, MAX(date) last_date FROM daily_downloads "
        "WHERE date<? GROUP BY crate", (_today(),)
    ).fetchall()
    return _out({"today_utc_is_partial_and_excluded": _today(), "crates": [dict(r) for r in rows]})


def scan_for_anomalies(threshold_pct: Optional[float] = None, last_n_days: Optional[int] = None,
                       direction: str = "both") -> str:
    """Scan ALL tracked crates for days that deviate >= threshold_pct from the same-weekday
    baseline. direction: 'down', 'up' or 'both'. Leave threshold_pct/last_n_days empty to use
    the configured defaults. Returns the largest deviations first, plus how many crates were
    anomalous on each date (many crates on one date => likely ECOSYSTEM_WIDE)."""
    cfg = config.load()
    threshold_pct = float(threshold_pct if threshold_pct is not None else cfg["anomaly_threshold_pct"])
    last_n_days = int(last_n_days if last_n_days is not None else cfg["scan_window_days"])
    con = connect(readonly=True)
    crates = [r[0] for r in con.execute("SELECT DISTINCT crate FROM daily_downloads")]
    found = []
    for c in crates:
        t = _totals(con, c)
        for d in sorted(t)[-last_n_days:]:
            b = _baseline(t, d)
            if not b:
                continue
            dev = (t[d] / b - 1) * 100
            if (direction in ("down", "both") and dev <= -threshold_pct) or \
               (direction in ("up", "both") and dev >= threshold_pct):
                found.append({"crate": c, "date": d, "downloads": t[d],
                              "baseline": int(b), "deviation_pct": round(dev, 1)})
    found.sort(key=lambda x: -abs(x["deviation_pct"]))
    by_date: dict[str, int] = {}
    for f in found:
        by_date[f["date"]] = by_date.get(f["date"], 0) + 1
    return _out({"threshold_pct": threshold_pct, "direction": direction,
                 "crates_anomalous_per_date": dict(sorted(by_date.items())),
                 "anomalies": found[:25], "total_found": len(found)})


def daily_series(crate: str, start: str, end: str) -> str:
    """Daily total downloads for a crate between start and end (YYYY-MM-DD, inclusive),
    each with weekday and deviation from its same-weekday baseline."""
    con = connect(readonly=True)
    t = _totals(con, crate)
    out = []
    for d in sorted(t):
        if start <= d <= end:
            b = _baseline(t, d)
            out.append({"date": d, "dow": date.fromisoformat(d).strftime("%a"), "downloads": t[d],
                        "dev_pct": round((t[d] / b - 1) * 100, 1) if b else None})
    return _out(out)


def peer_comparison(day: str) -> str:
    """For one date, show every tracked crate's deviation from its same-weekday baseline.
    If most crates moved together, the change is ECOSYSTEM_WIDE, not crate-specific."""
    con = connect(readonly=True)
    res = []
    for (c,) in con.execute("SELECT DISTINCT crate FROM daily_downloads").fetchall():
        t = _totals(con, c)
        b = _baseline(t, day) if day in t else None
        if b:
            res.append({"crate": c, "downloads": t[day], "dev_pct": round((t[day] / b - 1) * 100, 1)})
    res.sort(key=lambda x: x["dev_pct"])
    devs = [r["dev_pct"] for r in res]
    return _out({"date": day, "median_dev_pct": round(st.median(devs), 1) if devs else None, "crates": res})


def version_breakdown(crate: str, day: str, baseline_days: int = 7) -> str:
    """Which versions account for the change on `day`? Compares each version's downloads
    on `day` with its average over the `baseline_days` days before. version 'other' is the
    long tail. Includes each version's release date and yank status."""
    con = connect(readonly=True)
    d0 = date.fromisoformat(day)
    lo = (d0 - timedelta(days=baseline_days)).isoformat()
    rows = con.execute(
        "SELECT dd.version_id vid, dd.date, dd.downloads, COALESCE(v.num,'other') num, "
        "v.created_at, v.yanked FROM daily_downloads dd LEFT JOIN versions v ON v.id=dd.version_id "
        "WHERE dd.crate=? AND dd.date>=? AND dd.date<=?", (crate, lo, day)).fetchall()
    per: dict[str, dict] = {}
    for r in rows:
        p = per.setdefault(r["num"], {"version": r["num"], "released": r["created_at"],
                                      "yanked": r["yanked"], "base": [], "day": 0})
        if r["date"] == day:
            p["day"] = r["downloads"]
        else:
            p["base"].append(r["downloads"])
    out = []
    for p in per.values():
        base = sum(p["base"]) / baseline_days  # missing days count as 0 -> new versions look like growth
        out.append({"version": p["version"], "released": p["released"], "yanked": p["yanked"],
                    "baseline_avg": int(base), "on_day": p["day"], "delta": int(p["day"] - base)})
    out.sort(key=lambda x: x["delta"])
    return _out({"crate": crate, "date": day, "total_delta": sum(o["delta"] for o in out),
                 "note": "Only the top versions per day are itemised; 'other' is an aggregate. "
                         "A negative old version with a positive new version = VERSION_MIGRATION.",
                 "versions": out})


def releases(crate: str, start: str, end: str) -> str:
    """Releases (and yanks) for a crate published between start and end (inclusive)."""
    con = connect(readonly=True)
    rows = con.execute(
        "SELECT num, created_at, yanked, rust_version FROM versions WHERE crate=? "
        "AND substr(created_at,1,10)>=? AND substr(created_at,1,10)<=? ORDER BY created_at",
        (crate, start, end)).fetchall()
    return _out([dict(r) for r in rows])


def _is_select(query: str) -> bool:
    return bool(re.match(r"^\s*select\b", query, re.I)) and ";" not in query.strip().rstrip(";")


def run_sql(query: str) -> str:
    """Run a read-only SELECT against the database for ad-hoc questions.
    Tables: versions(id,crate,num,created_at,yanked,rust_version),
    daily_downloads(crate,date,version_id,downloads,fetched_at). version_id=0 is the 'other' bucket.
    Max 200 rows."""
    if not _is_select(query):
        return _out({"error": "Only a single SELECT statement is allowed."})
    try:
        rows = connect(readonly=True).execute(query).fetchmany(200)
        return _out([dict(r) for r in rows])
    except Exception as e:
        return _out({"error": str(e)})


def run_saved_query(name: str, params_json: str = "{}") -> str:
    """Run a saved, named query defined by the product team. Pass parameters as a JSON object."""
    q = next((q for q in config.load()["saved_queries"] if q["name"] == name), None)
    if not q:
        return _out({"error": f"No saved query named {name!r}",
                     "available": [x["name"] for x in config.load()["saved_queries"]]})
    if not _is_select(q["sql"]):
        return _out({"error": "Saved query must be a single SELECT."})
    try:
        rows = connect(readonly=True).execute(q["sql"], json.loads(params_json or "{}")).fetchmany(200)
        return _out([dict(r) for r in rows])
    except Exception as e:
        return _out({"error": str(e)})


# ------------------------------------------------------------------ memory
def recall_memory() -> str:
    """Read your own memory BEFORE investigating: lessons learned from past
    investigations, plus your graded track record and the valid cause keys."""
    cfg = config.load()
    return _out({"memory": memory.memory_block(int(cfg["memory_max_lessons"])),
                 "graded_outcomes_by_cause": memory.outcomes_by_cause(),
                 "valid_causes": cfg["causes"]})


def record_investigation(crate: str, event_date: str, hypothesis: str, confidence: str,
                         evidence: str, steps: str) -> str:
    """Log your conclusion. `hypothesis` MUST be one of the valid cause keys.
    `confidence` is low/medium/high. `evidence` = the specific numbers behind it.
    `steps` = the tools you called, in order. Returns the investigation id."""
    causes = config.load()["causes"]
    if hypothesis not in causes:
        return _out({"error": f"hypothesis must be one of {list(causes)}"})
    con = connect()
    cur = con.execute(
        "INSERT INTO investigations(ts,crate,event_date,hypothesis,confidence,evidence,steps,run_id) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(timespec="seconds"), crate, event_date,
         hypothesis, confidence, evidence, steps, RUN["id"]))
    con.commit()
    return _out({"investigation_id": cur.lastrowid, "status": "pending human feedback"})


def save_lesson(situation: str, lesson: str) -> str:
    """Save a short, reusable lesson for future runs (e.g. 'when a drop is on a Sunday,
    check the weekday baseline first'). Only save things that would change what you do next time."""
    memory.add_lesson(situation, lesson, "agent")
    return _out({"saved": True})


# ---------------------------------------------------------------- registry
TOOL_REGISTRY = {f.__name__: f for f in (
    list_crates, scan_for_anomalies, daily_series, peer_comparison, version_breakdown,
    releases, run_sql, run_saved_query, recall_memory, record_investigation, save_lesson)}

# Tools the agent needs to do its job; the dashboard warns before they are disabled.
ESSENTIAL = {"record_investigation", "scan_for_anomalies"}


def default_description(name: str) -> str:
    return " ".join((TOOL_REGISTRY[name].__doc__ or "").split())


def _with_doc(fn, doc: str):
    @functools.wraps(fn)
    def wrapper(*a, **k):
        return fn(*a, **k)
    wrapper.__doc__ = doc
    return wrapper


def build_tools(cfg: dict) -> list:
    """The tools the agent gets, honouring the PM's enable/disable switches and descriptions."""
    tools = []
    for name, fn in TOOL_REGISTRY.items():
        if name in cfg["disabled_tools"]:
            continue
        if name == "recall_memory" and cfg["memory_mode"] != "tool":
            continue                      # memory is injected into the prompt, or off
        if name == "save_lesson" and cfg["memory_mode"] == "off":
            continue
        if name == "run_saved_query":
            if not cfg["saved_queries"]:
                continue
            listing = "; ".join(f"{q['name']}: {q['description']}" for q in cfg["saved_queries"])
            doc = (cfg["tool_descriptions"].get(name) or default_description(name)) + f" Available queries: {listing}"
            tools.append(_with_doc(fn, doc))
            continue
        override = cfg["tool_descriptions"].get(name)
        tools.append(_with_doc(fn, override) if override else fn)
    return tools
