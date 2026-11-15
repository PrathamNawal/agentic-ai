"""Configure: system prompt, tools, analysis parameters, causes, saved queries, model, watchlist."""
import difflib
import json

import streamlit as st

import config
import llm
import tools
import ui

st.title("⚙️ Configure")
st.caption("Every change applies to the **next** run. Prompts are versioned, so you can always roll back.")
cfg = config.load()

tab_prompt, tab_tools, tab_analysis, tab_causes, tab_queries, tab_model, tab_data = st.tabs(
    ["System prompt", "Tools", "Analysis", "Causes", "Saved queries", "Model", "Watchlist"])

# ------------------------------------------------------------------ prompt
with tab_prompt:
    versions = config.list_prompts()
    active = next(v for v in versions if v["active"])
    st.markdown(f"Active: **#{active['id']} · {active['label']}**")
    st.caption("Use `{causes}` where the list of valid causes should go (it is filled in from the Causes tab). "
               "Memory instructions are added automatically based on the Memory page.")
    text = st.text_area("Instructions", active["text"], height=420)
    label = st.text_input("Name this version", placeholder="e.g. Stricter evidence rules")
    c1, c2 = st.columns(2)
    if c1.button("💾 Save as new version and activate", type="primary", disabled=text == active["text"]):
        config.save_prompt(text, label or "Edited", True)
        st.toast("Saved. The agent will use it on the next run.")
        st.rerun()
    if text != active["text"]:
        with st.expander("Changes vs the active version"):
            st.code("\n".join(difflib.unified_diff(active["text"].splitlines(), text.splitlines(),
                                                    "active", "edited", lineterm="")), language="diff")
    st.markdown("**Version history**")
    for v in versions:
        a, b = st.columns([6, 1])
        a.write(f"{'🟢' if v['active'] else '⚪'} #{v['id']} · {v['label']} · {v['ts'][:16]}")
        if not v["active"] and b.button("Use", key=f"u{v['id']}"):
            config.activate_prompt(v["id"])
            st.rerun()

# ------------------------------------------------------------------- tools
with tab_tools:
    st.caption("Turn tools on or off, and rewrite what each tool says about itself. "
               "The agent decides when to call a tool largely from this description.")
    disabled = set(cfg["disabled_tools"])
    descs = dict(cfg["tool_descriptions"])
    for name in tools.TOOL_REGISTRY:
        with st.container(border=True):
            a, b = st.columns([1, 5])
            on = a.toggle(name, value=name not in disabled, key=f"on_{name}")
            if on:
                disabled.discard(name)
            else:
                disabled.add(name)
            if not on and name in tools.ESSENTIAL:
                b.warning("The agent normally needs this tool.")
            d = b.text_area("Description", descs.get(name) or tools.default_description(name),
                            key=f"d_{name}", height=90, label_visibility="collapsed")
            if d.strip() and d.strip() != tools.default_description(name):
                descs[name] = d.strip()
            else:
                descs.pop(name, None)
            if name == "run_saved_query" and not cfg["saved_queries"]:
                b.caption("Inactive until you add a query in the Saved queries tab.")
            if name in ("recall_memory", "save_lesson") and cfg["memory_mode"] != "tool" and name == "recall_memory":
                b.caption("Not offered while memory mode isn't 'agent looks it up itself'.")
    if st.button("💾 Save tools", type="primary"):
        config.update(disabled_tools=sorted(disabled), tool_descriptions=descs)
        st.toast("Tools saved.")

# ---------------------------------------------------------------- analysis
with tab_analysis:
    st.caption("How anomalies are detected, and how long the agent may work.")
    thr = st.slider("Anomaly threshold (%)", 5.0, 50.0, float(cfg["anomaly_threshold_pct"]), 1.0,
                    help="A day counts as anomalous if it differs from its baseline by at least this much. "
                         "Lower = more anomalies and more noise.")
    wk = st.slider("Baseline: same weekday over the previous N weeks", 2, 8, int(cfg["baseline_weeks"]))
    win = st.slider("Scan window (days)", 7, 90, int(cfg["scan_window_days"]))
    lim = st.slider("Max tool calls per run", 5, 60, int(cfg["tool_call_limit"]),
                    help="Hard stop. Protects your budget if the agent gets stuck.")
    dt = st.text_area("Default task when you press Run", cfg["default_task"])
    if st.button("💾 Save analysis settings", type="primary"):
        config.update(anomaly_threshold_pct=thr, baseline_weeks=wk, scan_window_days=win,
                      tool_call_limit=lim, default_task=dt)
        st.toast("Saved.")

# ------------------------------------------------------------------ causes
with tab_causes:
    st.caption("The only conclusions the agent may reach. Add your own, or sharpen a definition. "
               "Sharper definitions give better, more consistent answers.")
    causes = dict(cfg["causes"])
    edited = {}
    for k, v in causes.items():
        a, b = st.columns([1, 3])
        a.code(k)
        edited[k] = b.text_input(k, v, key=f"cause_{k}", label_visibility="collapsed")
    with st.form("newcause", clear_on_submit=True):
        nk = st.text_input("New cause key", placeholder="PRICING_CHANGE")
        nv = st.text_input("What it means")
        add = st.form_submit_button("Add cause")
    if add and nk and nv:
        edited[nk.strip().upper().replace(" ", "_")] = nv
    drop = st.multiselect("Remove causes", list(edited))
    if st.button("💾 Save causes", type="primary") or add:
        for k in drop:
            edited.pop(k, None)
        config.update(causes=edited)
        st.toast("Causes saved.")
        if add:
            st.rerun()

# ----------------------------------------------------------------- queries
with tab_queries:
    st.caption("Give the agent your own named, read-only SQL queries. Use `:name` for parameters. "
               "Tables: `daily_downloads(crate,date,version_id,downloads)`, `versions(id,crate,num,created_at,yanked)`.")
    qs = list(cfg["saved_queries"])
    for i, q in enumerate(qs):
        with st.container(border=True):
            st.markdown(f"**{q['name']}** — {q['description']}")
            st.code(q["sql"], language="sql")
            if st.button("Delete", key=f"dq{i}"):
                qs.pop(i)
                config.update(saved_queries=qs)
                st.rerun()
    with st.form("newq", clear_on_submit=True):
        qn = st.text_input("Name", placeholder="top_versions_on_day")
        qd = st.text_input("When should the agent use it?")
        qsql = st.text_area("SQL (single SELECT)", "SELECT version_id, downloads FROM daily_downloads "
                            "WHERE crate = :crate AND date = :date ORDER BY downloads DESC LIMIT 5")
        if st.form_submit_button("Add query"):
            if qn and qd and tools._is_select(qsql):
                qs.append({"name": qn.strip(), "description": qd.strip(), "sql": qsql.strip()})
                config.update(saved_queries=qs)
                st.rerun()
            else:
                st.error("Name, description and a single SELECT are required.")

# ------------------------------------------------------------------- model
with tab_model:
    options = ["auto"] + list(llm.KEYS)
    provider = st.selectbox("Provider", options, index=options.index(cfg["provider"]))
    model = st.text_input("Model", cfg["model"], placeholder=f"default: {llm.DEFAULTS.get(provider, 'per provider')}",
                          help="Must support tool calling. For OpenRouter use ids like x-ai/grok-4.1-fast.")
    base = st.text_input("Custom base URL (optional, OpenRouter/xAI)", cfg["base_url"])
    st.caption("API keys are never stored here. Enter yours in the sidebar, or set it on the server.")
    st.table({"Provider": list(llm.DEFAULTS), "Default model": list(llm.DEFAULTS.values()),
              "Server env var": list(llm.KEYS.values())})
    if st.button("💾 Save model settings", type="primary"):
        config.update(provider=provider, model=model.strip(), base_url=base.strip())
        st.session_state["provider"] = provider
        st.toast("Saved.")

# --------------------------------------------------------------- watchlist
with tab_data:
    wl = st.text_area("Crates to track (one per line)", "\n".join(cfg["watchlist"]), height=200)
    st.caption("After changing this, refresh data on the **Data explorer** page. "
               "More crates make the 'ecosystem-wide?' check stronger but ingestion slower (~2 seconds per crate).")
    if st.button("💾 Save watchlist", type="primary"):
        config.update(watchlist=[x.strip() for x in wl.splitlines() if x.strip()])
        st.toast("Saved.")

st.divider()
if st.button("↩️ Reset all settings to defaults (keeps prompt history and memory)"):
    config.reset()
    st.rerun()
