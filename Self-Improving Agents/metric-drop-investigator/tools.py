"""Tools the Agno agent can call. Every function returns a compact JSON string.

Analysis parameters (threshold, baseline weeks, scan window, minimum volume) come from config.py, so
a product manager can change them from the dashboard without touching code.

Domain: daily consumer complaints about financial companies (real CFPB data). "Entity" = company.

Assumptions:
- The metric is daily complaint VOLUME per company (the 'total' dimension of daily_counts).
- Days after the dataset's last complete date are excluded (the newest days are still being published).
- An anomaly is a day that deviates from the median of the same weekday over the previous N weeks,
  which removes weekly seasonality. Low-volume companies are skipped (min_baseline_volume) because
  small counts are mostly noise.
- Outcome fields (response, timeliness) are labels set by the company; very recent complaints are still
  'In progress', so recent outcome rates are biased.
"""
import functools
import json
import re
import statistics as st
from datetime import date, datetime, timedelta, timezone
import config
import memory
from db import connect

# The dashboard/runner sets this so investigations can be linked to their run.
RUN = {"id": None}
DIMENSIONS = ("product", "issue", "channel", "response", "timely")


def _cutoff(con) -> str:
    """Last complete date of the dataset (days after it are excluded)."""
    r = con.execute("SELECT value FROM meta WHERE key='last_complete_date'").fetchone()
    if r:
        return json.loads(r[0])
    return con.execute("SELECT MAX(date) FROM daily_counts").fetchone()[0] or "9999-12-31"


def _totals(con, entity: str) -> dict[str, int]:
    """Daily totals with missing days filled as 0, from the first complaint to the cutoff."""
    cut = _cutoff(con)
    rows = con.execute("SELECT date, count FROM daily_counts WHERE entity=? AND dimension='total' AND date<=?",
                       (entity, cut)).fetchall()
    if not rows:
        return {}
    have = {r["date"]: r["count"] for r in rows}
    d, end, out = date.fromisoformat(min(have)), date.fromisoformat(cut), {}
    while d <= end:
        out[d.isoformat()] = have.get(d.isoformat(), 0)
        d += timedelta(days=1)
    return out


def _baseline(totals: dict[str, int], d: str) -> float | None:
    """Median of the same weekday over the previous N weeks (needs >= min(3, N) points)."""
    weeks = int(config.load()["baseline_weeks"])
    dd = date.fromisoformat(d)
    pts = [totals[k] for w in range(1, weeks + 1)
           if (k := (dd - timedelta(weeks=w)).isoformat()) in totals]
    return st.median(pts) if len(pts) >= min(3, weeks) else None


def _out(obj) -> str:
    return json.dumps(obj, default=str, separators=(",", ":"))


def _rows() -> int:
    return int(config.load()["tool_result_max_rows"])


# --------------------------------------------------------------- data tools
def list_entities() -> str:
    """List the companies in the dataset with their date coverage, total complaint volume, and the
    dataset's last complete date (later days are excluded)."""
    con = connect(readonly=True)
    rows = con.execute(
        "SELECT entity, MIN(date) first_date, MAX(date) last_date, SUM(count) complaints FROM daily_counts "
        "WHERE dimension='total' GROUP BY entity ORDER BY complaints DESC").fetchall()
    return _out({"last_complete_date": _cutoff(con), "dimensions_available": list(DIMENSIONS),
                 "companies": [dict(r) for r in rows]})


def scan_for_anomalies(threshold_pct: float = 0, last_n_days: int = 0, direction: str = "both") -> str:
    """Scan ALL companies for days whose complaint volume deviates >= threshold_pct (a percentage, e.g. 30)
    from the same-weekday baseline. direction: 'down', 'up' or 'both'. Pass 0 for threshold_pct and
    last_n_days to use the configured defaults. Returns the largest deviations first, plus the dates where
    several companies were anomalous together (likely INDUSTRY_WIDE)."""
    cfg = config.load()
    threshold_pct = float(threshold_pct) if threshold_pct and threshold_pct > 0 else float(cfg["anomaly_threshold_pct"])
    last_n_days = int(last_n_days) if last_n_days and last_n_days > 0 else int(cfg["scan_window_days"])
    min_vol = float(cfg["min_baseline_volume"])
    con = connect(readonly=True)
    entities = [r[0] for r in con.execute("SELECT DISTINCT entity FROM daily_counts")]
    found = []
    for e in entities:
        t = _totals(con, e)
        for d in sorted(t)[-last_n_days:]:
            b = _baseline(t, d)
            if not b or b < min_vol:
                continue
            dev = (t[d] / b - 1) * 100
            if (direction in ("down", "both") and dev <= -threshold_pct) or \
               (direction in ("up", "both") and dev >= threshold_pct):
                found.append({"company": e, "date": d, "complaints": t[d],
                              "baseline": int(b), "deviation_pct": round(dev, 1)})
    found.sort(key=lambda x: -abs(x["deviation_pct"]))
    by_date: dict[str, int] = {}
    for f in found:
        by_date[f["date"]] = by_date.get(f["date"], 0) + 1
    # only dates where several companies moved together (the INDUSTRY_WIDE hint), busiest first
    multi = dict(sorted(((d, n) for d, n in by_date.items() if n >= 3), key=lambda x: -x[1])[:_rows()])
    return _out({"threshold_pct": threshold_pct, "min_baseline_volume": min_vol, "direction": direction,
                 "last_complete_date": _cutoff(con), "dates_with_3plus_companies_anomalous": multi,
                 "total_found": len(found), "showing_top": min(len(found), _rows()),
                 "anomalies": found[:_rows()]})


def daily_series(company: str, start: str, end: str) -> str:
    """Daily complaint volume for a company between start and end (YYYY-MM-DD, inclusive),
    each with weekday and deviation from its same-weekday baseline."""
    con = connect(readonly=True)
    t = _totals(con, company)
    out = []
    for d in sorted(t):
        if start <= d <= end:
            b = _baseline(t, d)
            out.append({"date": d, "dow": date.fromisoformat(d).strftime("%a"), "complaints": t[d],
                        "dev_pct": round((t[d] / b - 1) * 100, 1) if b else None})
    if len(out) > 31:   # keep it small: the most recent 31 days of the range
        return _out({"note": f"range has {len(out)} days; showing the last 31. Narrow start/end for more.",
                     "days": out[-31:]})
    return _out(out)


def peer_comparison(day: str) -> str:
    """For one date, show every company's deviation from its same-weekday baseline.
    If most companies moved together, the change is INDUSTRY_WIDE, not company-specific."""
    con = connect(readonly=True)
    min_vol = float(config.load()["min_baseline_volume"])
    res = []
    for (e,) in con.execute("SELECT DISTINCT entity FROM daily_counts").fetchall():
        t = _totals(con, e)
        b = _baseline(t, day) if day in t else None
        if b and b >= min_vol:
            res.append({"company": e, "complaints": t[day], "baseline": int(b),
                        "dev_pct": round((t[day] / b - 1) * 100, 1)})
    res.sort(key=lambda x: x["dev_pct"])
    devs = [r["dev_pct"] for r in res]
    return _out({"date": day, "median_dev_pct": round(st.median(devs), 1) if devs else None, "companies": res})


def segment_breakdown(company: str, day: str, dimension: str = "product") -> str:
    """Which segments explain the change on `day`? Compares each segment's complaints that day with its
    same-weekday baseline. dimension: product | issue | channel | response | timely.
    One segment carrying most of the change => MIX_SHIFT (or CHANNEL_SHIFT for dimension=channel)."""
    if dimension not in DIMENSIONS:
        return _out({"error": f"dimension must be one of {list(DIMENSIONS)}"})
    weeks = int(config.load()["baseline_weeks"])
    con = connect(readonly=True)
    dd = date.fromisoformat(day)
    days = [day] + [(dd - timedelta(weeks=w)).isoformat() for w in range(1, weeks + 1)]
    rows = con.execute(
        f"SELECT segment, date, count FROM daily_counts WHERE entity=? AND dimension=? AND date IN ({','.join('?' * len(days))})",
        (company, dimension, *days)).fetchall()
    seg: dict[str, dict] = {}
    for r in rows:
        seg.setdefault(r["segment"], {})[r["date"]] = r["count"]
    out = []
    for name, by in seg.items():
        base = st.median([by.get(d, 0) for d in days[1:]])
        out.append({"segment": name, "on_day": by.get(day, 0), "baseline": int(base),
                    "delta": int(by.get(day, 0) - base)})
    total_delta = sum(o["delta"] for o in out)
    for o in out:
        o["share_of_change_pct"] = round(o["delta"] / total_delta * 100, 1) if total_delta else None
    out.sort(key=lambda x: -abs(x["delta"]))
    shown = out[:_rows()]
    return _out({"company": company, "date": day, "dimension": dimension, "total_delta": total_delta,
                 "segments_total": len(out), "segments_shown": len(shown),
                 "note": "Product/issue names were reorganised by the CFPB over the years; a shift across a "
                         "rename can be a DATA_ARTIFACT.", "segments": shown})


def rate_trend(company: str, start: str, end: str, dimension: str = "response") -> str:
    """Weekly outcome mix for a company: share of complaints by company response (dimension='response')
    or timeliness (dimension='timely'). Use it to see whether resolution quality changed. Caution: the
    newest complaints are still 'In progress', so the most recent weeks are biased."""
    if dimension not in ("response", "timely"):
        return _out({"error": "dimension must be 'response' or 'timely'"})
    con = connect(readonly=True)
    rows = con.execute("SELECT date, segment, count FROM daily_counts WHERE entity=? AND dimension=? "
                       "AND date>=? AND date<=?", (company, dimension, start, min(end, _cutoff(con)))).fetchall()
    weeks: dict[str, dict[str, int]] = {}
    for r in rows:
        d = date.fromisoformat(r["date"])
        wk = (d - timedelta(days=d.weekday())).isoformat()
        weeks.setdefault(wk, {})
        weeks[wk][r["segment"]] = weeks[wk].get(r["segment"], 0) + r["count"]
    out = []
    for wk in sorted(weeks):
        tot = sum(weeks[wk].values())
        out.append({"week_start": wk, "total": tot,
                    **{k: round(v / tot * 100, 1) for k, v in sorted(weeks[wk].items())}})
    note = f"{len(out)} weeks in range; showing the last 12. Narrow start/end for others." if len(out) > 12 else ""
    return _out({"company": company, "dimension": dimension, "unit": "% of complaints", "note": note,
                 "weeks": out[-12:]})


def get_events(company: str, start: str, end: str) -> str:
    """Known events (regulation, breaches, policy changes, campaigns) between start and end that apply to
    this company or to every company. This is curated by the product team; absence of an event proves nothing."""
    rows = connect(readonly=True).execute(
        "SELECT date, title, kind, note, source, entity FROM events WHERE (entity=? OR entity='*') "
        "AND date>=? AND date<=? ORDER BY date LIMIT ?", (company, start, end, _rows() + 5)).fetchall()
    return _out([dict(r) for r in rows])


def _is_select(query: str) -> bool:
    return bool(re.match(r"^\s*select\b", query, re.I)) and ";" not in query.strip().rstrip(";")


def run_sql(query: str) -> str:
    """Run a read-only SELECT against the database for ad-hoc questions.
    Table daily_counts(entity,date,dimension,segment,count): dimension is 'total' (segment 'all') or
    product | issue | channel | response | timely. Table events(entity,date,title,kind,note,source).
    Max 50 rows."""
    if not _is_select(query):
        return _out({"error": "Only a single SELECT statement is allowed."})
    try:
        rows = connect(readonly=True).execute(query).fetchmany(50)
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
        rows = connect(readonly=True).execute(q["sql"], json.loads(params_json or "{}")).fetchmany(50)
        return _out([dict(r) for r in rows])
    except Exception as e:
        return _out({"error": str(e)})


# ------------------------------------------------------------------ memory
def recall_memory() -> str:
    """Read your own memory BEFORE investigating: lessons learned from past
    investigations, plus your graded track record."""
    cfg = config.load()
    return _out({"memory": memory.memory_block(int(cfg["memory_max_lessons"])),
                 "graded_outcomes_by_cause": memory.outcomes_by_cause()[:10]})


def record_investigation(company: str, event_date: str, hypothesis: str, confidence: str,
                         evidence: str, steps: str) -> str:
    """Log your conclusion. `hypothesis` MUST be one of the valid cause keys.
    `confidence` is low/medium/high. `evidence` = the specific numbers behind it.
    `steps` = the tools you called, in order. Returns the investigation id."""
    causes = config.load()["causes"]
    if hypothesis not in causes:
        return _out({"error": f"hypothesis must be one of {list(causes)}"})
    con = connect()
    cur = con.execute(
        "INSERT INTO investigations(ts,entity,event_date,hypothesis,confidence,evidence,steps,run_id) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(timespec="seconds"), company, event_date,
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
    list_entities, scan_for_anomalies, daily_series, peer_comparison, segment_breakdown, rate_trend,
    get_events, run_sql, run_saved_query, recall_memory, record_investigation, save_lesson)}

# Tools the agent needs to do its job; the dashboard warns before they are disabled.
ESSENTIAL = {"record_investigation", "scan_for_anomalies"}


def default_description(name: str) -> str:
    return " ".join((TOOL_REGISTRY[name].__doc__ or "").split())


def _capped(fn, doc: str | None, max_chars: int):
    """Wrap a tool so its result can never exceed max_chars (keeps token use predictable)."""
    @functools.wraps(fn)
    def wrapper(*a, **k):
        out = fn(*a, **k)
        if len(out) > max_chars:
            return out[:max_chars] + f'..."[truncated {len(out) - max_chars} chars: narrow your query]"'
        return out
    if doc:
        wrapper.__doc__ = doc
    return wrapper


def build_tools(cfg: dict) -> list:
    """The tools the agent gets, honouring the PM's enable/disable switches and descriptions."""
    tools = []
    cap = int(cfg["tool_result_max_chars"])
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
            tools.append(_capped(fn, doc, cap))
            continue
        override = cfg["tool_descriptions"].get(name)
        tools.append(_capped(fn, override, cap))
    return tools
