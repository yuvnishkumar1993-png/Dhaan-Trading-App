import streamlit as st

def render_signals():
    st.header("⚡ Signal Generation Engine")
    st.table([{"Symbol": "RELIANCE", "Signal": "BUY", "Confidence": "85%"}])

if __name__ == "__main__":
    render_signals()
