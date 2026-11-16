"""Data explorer: see the real numbers the agent works with, and teach it about real-world events."""
import json

import altair as alt
import pandas as pd
import streamlit as st

import ingest
import tools
import ui
from db import connect

st.title("🔎 Data explorer")
meta = ingest.meta()
st.caption("Real consumer complaints about US financial companies, from the public CFPB database "
           "(complaints are sent to the company, which must respond). Each row is one complaint; here they are "
           "counted per company per day.")

info = ui.df("SELECT COUNT(DISTINCT entity) n, MIN(date) lo, MAX(date) hi FROM daily_counts WHERE dimension='total'").iloc[0]
a, b, c, d = st.columns(4)
a.metric("Companies", int(info["n"]))
b.metric("Complaints in source", f"{meta.get('complaints_in_source', 0):,}")
c.metric("Window", f"{info['lo']} → {info['hi']}")
d.metric("Last complete day", meta.get("last_complete_date", "n/a"))
with st.expander("About this dataset: provenance, caveats"):
    st.markdown(
        f"- **Source:** [{meta.get('source', '')}]({meta.get('source', '')}) (CC0), a mirror of the CFPB database "
        f"([original]({meta.get('original', '')})).\n"
        "- **Scope:** the top companies by complaint volume since 2018. Products and issues are split out; rare ones "
        "are grouped as 'Other'.\n"
        "- **Skew:** people who complain to a regulator are usually the unhappier ones, and credit reporting "
        "dominates volume after 2021.\n"
        "- **Labels:** company response and timeliness are set by the company. The newest complaints are still "
        "'In progress'.\n"
        "- **Taxonomy changes:** the CFPB renamed products over the years, which can look like a mix shift.")

entities = ui.df("SELECT entity, SUM(count) n FROM daily_counts WHERE dimension='total' GROUP BY entity ORDER BY n DESC")["entity"].tolist()
if not entities:
    st.warning("No data loaded.")
    st.stop()
company = st.selectbox("Company", entities)
since = st.date_input("Show from", value=pd.to_datetime("2022-01-01"), min_value=pd.to_datetime(info["lo"]))

s = ui.df("SELECT date, count FROM daily_counts WHERE entity=? AND dimension='total' AND date>=? ORDER BY date",
          (company, str(since)))
s["date"] = pd.to_datetime(s["date"])
ev = ui.df("SELECT date, title FROM events WHERE (entity=? OR entity='*') AND date>=?", (company, str(since)))
ev["date"] = pd.to_datetime(ev["date"])
line = alt.Chart(s).mark_line().encode(x=alt.X("date:T", title=None), y=alt.Y("count:Q", title="complaints per day"),
                                       tooltip=["date:T", "count:Q"])
rules = alt.Chart(ev).mark_rule(color="#d62728", strokeDash=[4, 3]).encode(x="date:T", tooltip=["title", "date:T"])
st.altair_chart(line + rules, width="stretch")
st.caption("Red lines are events in the table below. The agent can see them; it can't see anything you haven't recorded.")

st.subheader("Where the complaints come from")
dim = st.radio("Split by", list(tools.DIMENSIONS), horizontal=True)
split = ui.df("SELECT segment, SUM(count) n FROM daily_counts WHERE entity=? AND dimension=? AND date>=? "
              "GROUP BY segment ORDER BY n DESC", (company, dim, str(since)))
st.bar_chart(split.set_index("segment")["n"])

st.subheader("📌 Events the agent can use as explanations")
st.caption("**This is where you teach the agent real-world context.** A launch, an outage, a policy change, a "
           "press story: record it here, and the agent will cite it when a spike lines up. Use `*` for events that "
           "affect every company. The starter events are from public knowledge and unverified: check or delete them.")
events = ui.df("SELECT id, entity, date, title, kind, source FROM events ORDER BY date DESC")
st.dataframe(events, hide_index=True)
with st.form("newevent", clear_on_submit=True):
    c1, c2 = st.columns(2)
    e_ent = c1.selectbox("Applies to", ["*"] + entities, format_func=lambda x: "All companies" if x == "*" else x)
    e_date = c2.date_input("Date")
    e_title = st.text_input("What happened?", placeholder="e.g. Mobile app redesign launched")
    e_kind = st.selectbox("Kind", ["product", "incident", "policy", "regulation", "campaign", "macro", "other"])
    e_src = st.text_input("Source / note (optional)")
    if st.form_submit_button("Add event") and e_title:
        con = connect()
        con.execute("INSERT INTO events(entity,date,title,kind,note,source) VALUES (?,?,?,?,?,?)",
                    (e_ent, str(e_date), e_title, e_kind, "", e_src or "added by product team"))
        con.commit()
        st.rerun()
if len(events):
    rm = st.selectbox("Delete an event", [None] + events["id"].tolist(),
                      format_func=lambda i: "—" if i is None else f"#{i} {events.loc[events.id == i, 'title'].iloc[0][:60]}")
    if rm is not None and st.button("Delete"):
        con = connect()
        con.execute("DELETE FROM events WHERE id=?", (int(rm),))
        con.commit()
        st.rerun()

st.subheader("Anomalies the agent would find")
scan = json.loads(tools.scan_for_anomalies())
rows = [r for r in scan["anomalies"] if r["company"] == company] or scan["anomalies"][:10]
st.dataframe(rows, hide_index=True)
st.caption(f"{scan['total_found']} anomalies across all companies at ±{scan['threshold_pct']}% "
           f"(companies under {scan['min_baseline_volume']:.0f} complaints/day are skipped). "
           "Change the settings under Configure → Analysis.")
