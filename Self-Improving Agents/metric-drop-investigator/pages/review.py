"""Grade the agent's conclusions. This is the learning signal."""
import json

import streamlit as st

import config
import memory
import ui

st.title("✅ Review & grade")
st.caption("Was the agent right? **Confirm** or **correct** each conclusion. Both become lessons "
           "the agent reads on future runs.")

causes = config.load()["causes"]
pending = ui.df("SELECT * FROM investigations WHERE status='pending' ORDER BY id DESC")

if not len(pending):
    st.success("Nothing waiting for review.")
for _, r in pending.iterrows():
    with st.container(border=True):
        st.markdown(f"**#{r['id']} · {r['entity']} · {r['event_date']}**")
        st.markdown(f"Agent concluded **{r['hypothesis']}** ({r['confidence']} confidence)")
        st.caption(causes.get(r["hypothesis"], ""))
        st.write(r["evidence"])
        if r["steps"]:
            st.caption(f"Steps: {r['steps']}")
        a, b = st.columns([1, 3])
        if a.button("✅ Confirm", key=f"c{r['id']}"):
            memory.confirm(int(r["id"]))
            st.rerun()
        with b.popover("✏️ Correct it"):
            true = st.selectbox("What was the real cause?", list(causes), key=f"s{r['id']}",
                                format_func=lambda k: f"{k} — {causes[k][:60]}")
            note = st.text_input("Why? (this becomes the lesson)", key=f"n{r['id']}")
            if st.button("Save correction", key=f"x{r['id']}"):
                memory.correct(int(r["id"]), true, note)
                st.rerun()

st.subheader("Graded history")
done = ui.df("SELECT id, entity, event_date, hypothesis, status, true_cause, feedback_note, graded_at "
             "FROM investigations WHERE status!='pending' ORDER BY id DESC")
if len(done):
    st.dataframe(done, hide_index=True)
else:
    st.caption("No graded investigations yet.")
