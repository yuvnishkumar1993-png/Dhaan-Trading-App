import streamlit as st
from database import init_db
from dhan_api import verify_dhan_credentials
from dhan_websocket import DhanWebSocket

from pages.option_chain import render_option_chain
from pages.charts_page import render_charts
from pages.signal_page import render_signals
from pages.portfolio import render_portfolio
from pages.watchlist import render_watchlist
from pages.backtest import render_backtest
from pages.journal import render_journal

init_db()
st.set_page_config(page_title="Dhan Platform", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.sidebar.title("📊 Dhan Platform")

if not st.session_state.logged_in:
    st.sidebar.subheader("🔑 Login")
    with st.sidebar.form("l_form"):
        cid = st.text_input("Client ID")
        token = st.text_input("Access Token", type="password")
        if st.form_submit_button("Login") and cid and token:
            valid, msg = verify_dhan_credentials(cid, token)
            if valid:
                st.session_state.logged_in = True
                st.session_state.client_id = cid
                st.session_state.access_token = token
                st.success("Success!")
                st.rerun()
            else:
                st.error(msg)
else:
    st.sidebar.success(f"ID: {st.session_state.client_id}")
    page = st.sidebar.selectbox("Menu", [
        "Option Chain", "Charts & Graphs", "Signal Generator", 
        "Portfolio & Positions", "Watchlist & Alerts", "Backtesting Engine", "Trading Journal"
    ])
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

if not st.session_state.logged_in:
    st.title("🚀 Welcome to Dhan Custom Trading App")
    st.write("कृपया साइडबार से लॉगिन करें।")
else:
    if "ws_client" not in st.session_state:
        st.session_state.ws_client = DhanWebSocket(st.session_state.client_id, st.session_state.access_token)
        st.session_state.ws_client.start()

    if page == "Option Chain": render_option_chain()
    elif page == "Charts & Graphs": render_charts()
    elif page == "Signal Generator": render_signals()
    elif page == "Portfolio & Positions": render_portfolio()
    elif page == "Watchlist & Alerts": render_watchlist()
    elif page == "Backtesting Engine": render_backtest()
    elif page == "Trading Journal": render_journal()
