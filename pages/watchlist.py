import streamlit as st
from database import add_to_watchlist, get_watchlist

def render_watchlist():
    st.header("⭐ Custom Watchlist")
    with st.form("w_form"):
        s = st.text_input("Symbol")
        if st.form_submit_button("Add") and s:
            add_to_watchlist(st.session_state.client_id, s)
            st.rerun()
    for stock in get_watchlist(st.session_state.client_id):
        st.code(stock)

if __name__ == "__main__":
    render_watchlist()
