"""Monitoring: is the agent healthy, accurate, and getting better?"""
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

import memory
import ui

st.title("📊 Overview")
st.caption("Is the agent healthy, accurate, and improving? Improvement shows up as rising accuracy "
           "and fewer tool calls per run, after you grade its work on the **Review & grade** page.")

runs = ui.df("SELECT * FROM runs ORDER BY id")
inv = ui.df("SELECT * FROM investigations ORDER BY id")
tr = memory.track_record()

# ---- health checks
st.subheader("Health")
c1, c2, c3 = st.columns(3)
last = ui.df("SELECT MAX(date) d, COUNT(*) n FROM daily_counts").iloc[0]
days_old = (datetime.now(timezone.utc).date() - datetime.fromisoformat(last["d"]).date()).days if last["d"] else None
with c1:
    if days_old is None:
        st.error("No data loaded. Open **Data explorer**.")
    else:
        st.info(f"Dataset: real CFPB complaints, latest day {last['d']}. It is a fixed historical snapshot "
                "(see **Data explorer** for what it covers).")
with c2:
    ok, info = ui.llm_ready()
    (st.success if ok else st.warning)(f"Model: {info}" if ok else info)
with c3:
    if tr["pending"]:
        st.warning(f"{tr['pending']} investigation(s) waiting for your grade.")
    else:
        st.success("No ungraded investigations.")

# ---- KPIs
st.subheader("Performance")
k = st.columns(5)
k[0].metric("Runs", len(runs))
fail = int((runs["status"] == "error").sum()) if len(runs) else 0
k[1].metric("Failed runs", fail)
k[2].metric("Graded investigations", tr["graded"])
k[3].metric("Accuracy (human-graded)", f"{tr['accuracy']:.0%}" if tr["accuracy"] is not None else "n/a",
            help="confirmed / (confirmed + corrected)")
ok_runs = runs[runs["status"] == "ok"] if len(runs) else runs
k[4].metric("Avg tool calls / run", f"{ok_runs['tool_calls'].mean():.1f}" if len(ok_runs) else "n/a")

if not len(runs):
    st.info("No runs yet. Go to **Run the agent** to start the first investigation.")
    st.stop()

left, right = st.columns(2)
with left:
    st.markdown("**Accuracy as you grade** (cumulative)")
    g = inv[inv["status"].isin(["confirmed", "corrected"])].sort_values("graded_at").copy()
    if len(g) >= 2:
        g["accuracy"] = (g["status"] == "confirmed").expanding().mean()
        g["graded #"] = range(1, len(g) + 1)
        st.line_chart(g.set_index("graded #")["accuracy"], y_label="accuracy")
    else:
        st.caption("Grade at least 2 investigations to see the trend.")
with right:
    st.markdown("**Tool calls per run** (fewer = more efficient)")
    if len(ok_runs) >= 2:
        st.line_chart(ok_runs.set_index("id")["tool_calls"], x_label="run #", y_label="tool calls")
    else:
        st.caption("Needs at least 2 successful runs.")

left, right = st.columns(2)
with left:
    st.markdown("**What the agent concludes**")
    if len(inv):
        st.bar_chart(inv["hypothesis"].value_counts())
with right:
    st.markdown("**Cost and speed**")
    if len(ok_runs):
        tokens = int(ok_runs["input_tokens"].fillna(0).sum() + ok_runs["output_tokens"].fillna(0).sum())
        st.metric("Total tokens", f"{tokens:,}")
        st.metric("Median run time", f"{ok_runs['duration_s'].median():.0f}s")

st.subheader("Recent runs")
show = runs.sort_values("id", ascending=False).head(15)[
    ["id", "ts", "status", "task", "model", "tool_calls", "duration_s", "prompt_version", "error"]]
st.dataframe(show, hide_index=True)
