"""Data explorer: see the real numbers the agent works with, and refresh them."""
import time

import altair as alt
import pandas as pd
import streamlit as st

import config
import ingest
import tools
import ui
from db import connect

st.title("🔎 Data explorer")
st.caption("Real daily downloads from the crates.io API. Releases are marked in red, so you can see "
           "what the agent sees when it looks for causes.")

cfg = config.load()
info = ui.df("SELECT COUNT(*) n, MIN(date) lo, MAX(date) hi, COUNT(DISTINCT crate) crates FROM daily_downloads").iloc[0]
a, b, c = st.columns(3)
a.metric("Crates", int(info["crates"]))
b.metric("Rows", f"{int(info['n']):,}")
c.metric("Date range", f"{info['lo']} → {info['hi']}")

with st.expander("🔄 Refresh from crates.io"):
    st.caption("crates.io only serves the last 90 days; refreshing regularly builds longer history. "
               "It allows ~1 request per second, so this takes about 2 seconds per crate.")
    if st.button("Refresh now"):
        con = connect()
        bar = st.progress(0.0)
        crates = cfg["watchlist"]
        for i, cr in enumerate(crates):
            try:
                ingest.ingest_crate(con, cr)
            except Exception as e:  # noqa: BLE001
                st.warning(f"{cr}: {e}")
            bar.progress((i + 1) / len(crates), text=cr)
        st.success("Done.")
        st.rerun()

crates = ui.df("SELECT DISTINCT crate FROM daily_downloads ORDER BY crate")["crate"].tolist()
if not crates:
    st.warning("No data yet. Press Refresh now.")
    st.stop()
crate = st.selectbox("Crate", crates)

d = ui.df("SELECT date, SUM(downloads) downloads FROM daily_downloads WHERE crate=? GROUP BY date ORDER BY date",
          (crate,))
d["date"] = pd.to_datetime(d["date"])
rel = ui.df("SELECT num, substr(created_at,1,10) date, yanked FROM versions WHERE crate=? "
            "AND substr(created_at,1,10)>=? ORDER BY created_at", (crate, str(info["lo"])))
rel["date"] = pd.to_datetime(rel["date"])

line = alt.Chart(d).mark_line().encode(x=alt.X("date:T", title=None), y=alt.Y("downloads:Q", title="daily downloads"),
                                       tooltip=["date:T", "downloads:Q"])
rules = alt.Chart(rel).mark_rule(color="#d62728", strokeDash=[4, 3]).encode(x="date:T", tooltip=["num", "date:T"])
st.altair_chart(line + rules, width="stretch")
st.caption(f"{len(rel)} release(s) of {crate} in this window. The last day is partial and ignored by the agent.")

st.subheader("Anomalies the agent would find")
import json  # noqa: E402
scan = json.loads(tools.scan_for_anomalies())
rows = [r for r in scan["anomalies"] if r["crate"] == crate] or scan["anomalies"][:10]
st.dataframe(rows, hide_index=True)
st.caption(f"{scan['total_found']} anomalies across all crates at ±{scan['threshold_pct']}%. "
           f"Dates where many crates are anomalous at once: "
           f"{', '.join(k for k, v in scan['crates_anomalous_per_date'].items() if v >= len(crates) * 0.6) or 'none'}")
