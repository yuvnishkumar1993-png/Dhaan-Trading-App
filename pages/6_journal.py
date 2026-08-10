import streamlit as st
from database import save_journal_entry, get_journal_entries

def render_journal():
    st.header("📓 Trading Journal")
    with st.form("j_form"):
        d = st.date_input("Date")
        n = st.text_input("Stock")
        t = st.selectbox("Type", ["BUY", "SELL"])
        notes = st.text_area("Notes")
        if st.form_submit_button("Save") and n:
            save_journal_entry(st.session_state.client_id, d, n, t, notes)
            st.rerun()
    st.dataframe(get_journal_entries(st.session_state.client_id))

if __name__ == "__main__":
    render_journal()
