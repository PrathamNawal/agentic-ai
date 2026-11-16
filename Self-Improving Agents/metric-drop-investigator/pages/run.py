"""Run the agent on a task and watch exactly what it did."""
import json

import streamlit as st

import config
import runner
import tools
import ui

st.title("▶️ Run the agent")
cfg = config.load()

mode = st.radio("What should it investigate?",
                ["Let the agent choose", "Pick an anomaly", "Ask my own question"], horizontal=True)
task = cfg["default_task"]

if mode == "Pick an anomaly":
    scan = json.loads(tools.scan_for_anomalies())
    rows = scan["anomalies"]
    if rows:
        labels = [f"{r['company']} · {r['date']} · {r['deviation_pct']:+.1f}% vs baseline" for r in rows]
        i = st.selectbox("Anomalies found by the scan (largest first)", range(len(rows)), format_func=lambda i: labels[i])
        r = rows[i]
        task = f"Why did complaints about {r['company']} change by {r['deviation_pct']:+.1f}% on {r['date']}?"
        st.caption(f"{scan['total_found']} anomalies at ±{scan['threshold_pct']}%. "
                   "Change the threshold under Configure → Analysis.")
    else:
        st.info("No anomalies at the current threshold. Lower it under Configure → Analysis.")
elif mode == "Ask my own question":
    task = st.text_area("Question", "Why did complaints about Equifax change on 2023-04-12?")

with st.expander("What will the agent see? (system prompt + tools)"):
    text, version = runner.build_instructions(cfg)
    st.caption(f"Prompt version #{version} · memory mode: {cfg['memory_mode']} · "
               f"max {cfg['tool_call_limit']} tool calls")
    st.code(text, language="markdown")
    st.write("**Tools:** " + ", ".join(f.__name__ for f in tools.build_tools(cfg)))

ok, info = ui.llm_ready()
if not ok:
    st.warning(info)
if st.button("Run investigation", type="primary", disabled=not ok):
    with st.spinner("Investigating… (usually 20–90 seconds)"):
        out = runner.run_agent(task, api_key=ui.current_api_key(), provider=ui.current_provider())
    if out["status"] == "error":
        st.error(out["error"])
        st.caption("Common causes: wrong or empty API key, a model that doesn't support tool calling, "
                   "or a bad model name (change it under Configure → Model).")
    else:
        st.success(f"Done in {len(out['steps'])} tool calls.")
        st.subheader("Answer")
        st.markdown(out["answer"])
        st.subheader("What the agent did")
        for n, s in enumerate(out["steps"], 1):
            with st.expander(f"{n}. {s['tool']}({', '.join(f'{k}={v}' for k, v in (s['args'] or {}).items())})"
                             + ("  ❌" if s["error"] else "")):
                st.code(s["result"][:3000])
        st.info("Now open **Review & grade**. Your grade is what makes the agent improve.")
