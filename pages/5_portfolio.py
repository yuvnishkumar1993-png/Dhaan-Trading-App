import streamlit as st
import pandas as pd
from dhan_api import fetch_holdings, fetch_positions

def render_portfolio():
    st.header("💼 Live Portfolio & Positions")
    tab1, tab2 = st.tabs(["Demat Holdings", "Open Positions"])
    with tab1:
        if st.button("Load Holdings"):
            res = fetch_holdings(st.session_state.client_id, st.session_state.access_token)
            if res.get("error") == "Token Expired":
                st.error("⚠️ Token Expired. Please re-login.")
            else:
                st.dataframe(pd.DataFrame(res.get("data", [])))
    with tab2:
        if st.button("Load Positions"):
            res = fetch_positions(st.session_state.client_id, st.session_state.access_token)
            if res.get("error") == "Token Expired":
                st.error("⚠️ Token Expired. Please re-login.")
            else:
                st.dataframe(pd.DataFrame(res.get("data", [])))

if __name__ == "__main__":
    render_portfolio()
