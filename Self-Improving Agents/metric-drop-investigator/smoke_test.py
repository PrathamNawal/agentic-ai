"""Exercise every tool against the REAL complaints data (no LLM key needed)."""
import json

import tools as t
from db import connect
from ingest import ensure_data

assert ensure_data(), "no data: build_dataset.py must have been run (data/snapshots/)"


def show(name, s, n=500):
    print(f"\n--- {name}\n{s[:n]}{'...' if len(s) > n else ''}")


scan = json.loads(t.scan_for_anomalies(30, 1500))
show("scan_for_anomalies", json.dumps({k: v for k, v in scan.items() if k != "anomalies"}), 300)
assert scan["total_found"] > 0 and scan["anomalies"]
top = scan["anomalies"][0]
c, d = top["company"], top["date"]
print(f"\nInvestigating {c} on {d} ({top['deviation_pct']:+.0f}%)")

show("list_entities", t.list_entities(), 300)
show("peer_comparison", t.peer_comparison(d))
for dim in t.DIMENSIONS[:3]:
    r = json.loads(t.segment_breakdown(c, d, dim))
    assert r["segments"], dim
show("segment_breakdown(channel)", t.segment_breakdown(c, d, "channel"))
show("rate_trend", t.rate_trend(c, "2023-06-01", "2023-08-01", "timely"), 300)
show("get_events", t.get_events(c, "2018-01-01", "2024-12-31"))
show("daily_series", t.daily_series(c, d, d))
show("run_sql ok", t.run_sql("SELECT entity, SUM(count) n FROM daily_counts WHERE dimension='total' GROUP BY entity LIMIT 3"))
assert "error" in json.loads(t.run_sql("DELETE FROM events"))
assert "error" in json.loads(t.segment_breakdown(c, d, "nonsense"))
show("recall_memory", t.recall_memory(), 200)

# memory write path (cleaned up so the smoke test leaves nothing behind)
con = connect()
before = con.execute("SELECT COUNT(*) FROM investigations").fetchone()[0]
rid = json.loads(t.record_investigation(c, d, "UNEXPLAINED", "low", "smoke test", "smoke"))["investigation_id"]
con.execute("DELETE FROM investigations WHERE id=?", (rid,)); con.commit()
assert con.execute("SELECT COUNT(*) FROM investigations").fetchone()[0] == before
assert "error" in json.loads(t.record_investigation(c, d, "NOT_A_CAUSE", "low", "x", "x"))

from agno.models.openrouter import OpenRouter
from runner import build_agent
agent, version = build_agent(model=OpenRouter(id='x', api_key='dummy'))  # construct only; no network call
print(f"\nAgno agent built: {agent.name}, {len(agent.tools)} tools, prompt v{version}")
print("\nSMOKE TEST PASSED")
