import streamlit as st
import pandas as pd
from dhan_api import fetch_live_option_chain
from calculator import calculate_pcr, calculate_max_pain, calculate_gex

def render_option_chain():
    st.header("📊 Institutional Option Chain & Analytics")
    st.write("सीधे Dhan API से लाइव डेटा, एक्सपायरी और क्वांटिटेटिव मेट्रिक्स।")
    
    if "client_id" not in st.session_state or "access_token" not in st.session_state:
        st.warning("⚠️ Please login first from the sidebar.")
        return
        
    client_id = st.session_state.client_id
    access_token = st.session_state.access_token
    
    # यूजर से सिक्युरिटी आईडी और सेगमेंट इनपुट लेना (या डिफ़ॉल्ट NIFTY IDX_I)
    col1, col2 = st.columns(2)
    with col1:
        underlying_scrip = st.text_input("Underlying Security ID (e.g., 13 for NIFTY)", "13")
    with col2:
        underlying_seg = st.selectbox("Underlying Segment", ["IDX_I", "NSE_EQ", "BSE_IDX"])
        
    if st.button("Fetch Option Chain Data"):
        with st.spinner("Fetching live option chain from Dhan..."):
            response = fetch_live_option_chain(client_id, access_token, underlying_scrip, underlying_seg)
            
            if "error" in response:
                if response["error"] == "Token Expired":
                    st.error("⚠️ Token Expired. Please re-login.")
                else:
                    st.error(response["error"])
            else:
                st.success("Option Chain Data Fetched Successfully!")
                st.json(response) # लाइव API रिस्पॉन्स यहाँ दिखेगा

if __name__ == "__main__":
    render_option_chain()
