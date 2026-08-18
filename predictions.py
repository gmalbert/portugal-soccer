"""Streamlit entrypoint for the league consumer."""

import streamlit as st

try:
    from config import LEAGUE_CONFIG
    from pitch_oracle_core import run_app
except ModuleNotFoundError as exc:
    if exc.name != "pitch_oracle_core":
        raise
    st.set_page_config(page_title="Pitch Oracle setup", page_icon="⚽")
    st.error("The shared Pitch Oracle package is not installed in this environment.")
    st.code("python -m pip install -r requirements.txt", language="bash")
    st.info("Run the command from this repository using the same Python environment as Streamlit, then restart the app.")
    st.stop()


run_app(LEAGUE_CONFIG)
