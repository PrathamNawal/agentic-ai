"""Exercise every tool against the REAL ingested data (no LLM key needed)."""
import json

import tools as t
from agent import build_agent
from db import connect


def show(name, s, n=700):
    print(f"\n--- {name}\n{s[:n]}{'...' if len(s) > n else ''}")


scan = json.loads(t.scan_for_anomalies(15, 30))
show("scan_for_anomalies", json.dumps(scan))
assert scan["total_found"] >= 0

if scan["anomalies"]:
    top = scan["anomalies"][0]
    c, d = top["crate"], top["date"]
else:
    c, d = "serde", sorted(json.loads(t.daily_series("serde", "2000-01-01", "2999-01-01")), key=lambda r: r["dev_pct"] or 0)[0]["date"]
print(f"\nInvestigating {c} on {d}")

show("peer_comparison", t.peer_comparison(d))
show("version_breakdown", t.version_breakdown(c, d))
show("releases", t.releases(c, "2026-08-18", "2026-12-31"))
show("daily_series", t.daily_series(c, d, d))
show("run_sql ok", t.run_sql("SELECT crate, COUNT(*) n FROM daily_downloads GROUP BY crate LIMIT 3"))
show("run_sql blocked", t.run_sql("DELETE FROM versions"))
show("recall_memory", t.recall_memory(), 300)

# memory write path (rolled back so the smoke test leaves no fake investigation behind)
con = connect()
before = con.execute("SELECT COUNT(*) FROM investigations").fetchone()[0]
rid = json.loads(t.record_investigation(c, d, "UNEXPLAINED", "low", "smoke test", "smoke"))["investigation_id"]
con.execute("DELETE FROM investigations WHERE id=?", (rid,)); con.commit()
assert con.execute("SELECT COUNT(*) FROM investigations").fetchone()[0] == before
assert "error" in json.loads(t.record_investigation(c, d, "NOT_A_CAUSE", "low", "x", "x"))

from llm import DEFAULTS
from agno.models.openrouter import OpenRouter
agent = build_agent(OpenRouter(id=DEFAULTS['openrouter'], api_key='dummy'))  # construct only; no network call
print(f"\nAgno agent built: {agent.name}, {len(agent.tools)} tools")
print("\nSMOKE TEST PASSED")
