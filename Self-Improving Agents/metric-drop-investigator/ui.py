"""Shared dashboard helpers: password gate, sidebar (model + key), small query helpers."""
import hmac
import os

import pandas as pd
import streamlit as st

import config
import ingest
import llm
from db import connect


def df(sql: str, params=()) -> pd.DataFrame:
    return pd.read_sql_query(sql, connect(readonly=True), params=params)


def gate() -> None:
    """Optional password (set APP_PASSWORD) so a public deployment isn't open to everyone."""
    pw = os.getenv("APP_PASSWORD")
    if not pw or st.session_state.get("authed"):
        return
    st.title("🔒 Metric Anomaly Investigator")
    entered = st.text_input("Password", type="password")
    if entered:
        if hmac.compare_digest(entered, pw):
            st.session_state["authed"] = True
            st.rerun()
        st.error("Wrong password.")
    st.stop()


def current_api_key() -> str | None:
    """Key typed in this browser session; falls back to environment variables."""
    return st.session_state.get("api_key") or None


def current_provider() -> str:
    """Provider chosen in the sidebar (falls back to the saved setting)."""
    return st.session_state.get("provider") or config.load()["provider"]


def llm_ready() -> tuple[bool, str]:
    try:
        provider = llm.detect_provider(current_provider())
    except ValueError as e:
        return False, str(e)
    if not provider:
        if current_api_key():
            return False, "Choose your provider (groq, openrouter, xai or anthropic) in the sidebar; 'auto' only works with server-side keys."
        return False, "Choose a provider and paste your API key in the sidebar."
    if not (current_api_key() or os.getenv(llm.KEYS[provider])):
        return False, f"Add your {provider} API key in the sidebar."
    return True, provider


def sidebar() -> None:
    cfg = config.load()
    with st.sidebar:
        st.caption("Self-improving agent · real CFPB complaints data")
        st.subheader("🔑 Model access")
        options = ["auto"] + list(llm.KEYS)
        default = st.session_state.get("provider") or cfg["provider"]
        provider = st.selectbox("Provider", options, index=options.index(default) if default in options else 0,
                                help="auto = use whichever API key is available")
        st.session_state["provider"] = provider
        key = st.text_input("API key (this browser session only)", type="password",
                            value=st.session_state.get("api_key", ""),
                            help="Never saved to disk or the database. Or set OPENROUTER_API_KEY / XAI_API_KEY / "
                                 "GROQ_API_KEY / ANTHROPIC_API_KEY on the server.")
        st.session_state["api_key"] = key
        ok, info = llm_ready()
        if ok:
            st.success(f"Ready · {info}")
        else:
            st.warning(info)
        st.caption("Model, prompt, tools and memory: see **Configure** and **Memory**.")


def bootstrap() -> None:
    """Page setup shared by every page; makes sure the database has data."""
    if not st.session_state.get("_seeded"):
        st.session_state["_seeded"] = True
        ingest.ensure_data()
