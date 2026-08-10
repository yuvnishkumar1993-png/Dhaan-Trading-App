import streamlit as st
from dhan_api import fetch_historical_data
from calculator import run_advanced_calculations, calculate_risk_reward

def render_charts():
    st.header("📈 Advanced Technical Charts & Indicators")
    col1, col2 = st.columns(2)
    with col1: security_id = st.text_input("Security ID", "1333")
    with col2: exchange_segment = st.selectbox("Exchange Segment", ["NSE_EQ", "BSE_EQ"])
    
    if st.button("Fetch & Calculate"):
        response = fetch_historical_data(st.session_state.client_id, st.session_state.access_token, security_id, exchange_segment)
        if "error" in response:
            if response["error"] == "Token Expired":
                st.error("⚠️ Your Session Token has expired. Please re-login.")
            else:
                st.error(response["message"])
        else:
            df = run_advanced_calculations(response)
            if df is not None:
                st.line_chart(df[['close', 'SMA_20']])
                if 'RSI' in df.columns:
                    st.line_chart(df['RSI'])
                st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    render_charts()
