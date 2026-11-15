"""Memory: what the agent has learned, and how it is allowed to use it."""
import streamlit as st

import backup
import config
import memory
import ui

st.title("🧠 Memory")
cfg = config.load()

st.subheader("How the agent uses memory")
labels = {
    "tool": "Agent looks it up itself (recommended: most agentic)",
    "inject": "Always placed in the prompt (cheaper, more predictable)",
    "off": "Off (no memory: use this to measure what memory is worth)",
}
mode = st.radio("Memory mode", list(labels), index=list(labels).index(cfg["memory_mode"]),
                format_func=labels.get, horizontal=False)
n = st.slider("Max lessons the agent sees", 0, 50, int(cfg["memory_max_lessons"]),
              help="Newest lessons first. Too many lessons can distract the agent.")
if (mode, n) != (cfg["memory_mode"], cfg["memory_max_lessons"]):
    config.update(memory_mode=mode, memory_max_lessons=n)
    st.toast("Memory settings saved.")

with st.expander("Exactly what the agent sees from memory"):
    st.code(memory.memory_block(n), language="markdown")

st.subheader("Teach the agent")
st.caption("Add your own rule of thumb. It is stored as a lesson and used like any learned one.")
with st.form("teach", clear_on_submit=True):
    sit = st.text_input("When…", placeholder="a drop happens on a Sunday")
    les = st.text_input("…do this", placeholder="compare against the Sunday baseline before anything else")
    if st.form_submit_button("Add lesson") and sit and les:
        memory.add_lesson(sit, les, "manual")
        st.rerun()

st.subheader("Lessons")
lessons = memory.list_lessons()
if not lessons:
    st.info("No lessons yet. They appear when you grade investigations, when the agent saves one, "
            "or when you add one above.")
for l in lessons:
    a, b = st.columns([12, 1])
    a.markdown(f"**{l['situation']}** — {l['lesson']}  \n:gray[{l['source']} · {l['ts'][:10]}]")
    if b.button("🗑", key=f"d{l['id']}", help="Delete this lesson"):
        memory.delete_lesson(l["id"])
        st.rerun()

st.subheader("Track record by cause")
rows = memory.outcomes_by_cause()
if rows:
    st.dataframe(rows, hide_index=True)
else:
    st.caption("Appears after you grade investigations.")

st.subheader("💾 Backup & restore")
st.caption("Lessons, graded investigations, prompt versions, run history and settings in one file. "
           "On free hosting the disk resets when the app restarts, so download a backup after "
           "a grading session, and restore it here if the agent seems to have forgotten everything.")
st.download_button("⬇️ Download backup", backup.export_json(), file_name="agent-backup.json",
                   mime="application/json")
up = st.file_uploader("Restore from a backup file", type="json")
if up and st.button("Restore (replaces current memory and settings)"):
    st.success(f"Restored: {backup.import_json(up.getvalue())}")
