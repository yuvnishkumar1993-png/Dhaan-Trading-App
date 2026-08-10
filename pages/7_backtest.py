import streamlit as st
import pandas as pd
import numpy as np
import math
import time
from datetime import datetime

# Page Config
st.set_page_config(page_title="Quant Terminal", layout="wide")

# Persistent Session Protection (लॉगिन सुरक्षित रखने के लिए)
if "client_id" not in st.session_state: st.session_state.client_id = ""
if "access_token" not in st.session_state: st.session_state.access_token = ""

# Data Engine (Optimized & Cached)
@st.cache_data(ttl=3600)
def load_master_data():
    try:
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        df = pd.read_csv(url, low_memory=False)
        df.columns = [str(col).strip().upper() for col in df.columns]
        return df
    except: return pd.DataFrame()

master_df = load_master_data()

st.title("⚡ Institutional Quant Terminal Pro")

# --- 1. SMART ASSET & SCRIP SELECTOR ---
col1, col2 = st.columns(2)
with col1:
    asset_type = st.selectbox("Segment", ["Indices", "F&O Stocks"])
with col2:
    if not master_df.empty:
        if asset_type == "Indices":
            syms = master_df[master_df['SEM_EXCH_SEGMENT'].isin(['IDX_I', 'BSE_IDX'])]['SEM_TRADING_SYMBOL'].unique()
        else:
            syms = master_df[master_df['SEM_EXCH_SEGMENT'].isin(['NSE_EQ'])]['SEM_TRADING_SYMBOL'].unique()
        selected_symbol = st.selectbox("Search Symbol", options=syms)
    else:
        selected_symbol = st.text_input("Enter Symbol", "NIFTY")

# --- 2. AUTO-DETECT LOT SIZE & PARAMETERS ---
auto_lot = 25
if not master_df.empty and selected_symbol in master_df['SEM_TRADING_SYMBOL'].values:
    row = master_df[master_df['SEM_TRADING_SYMBOL'] == selected_symbol].iloc[0]
    auto_lot = int(row.get('SEM_LOT_UNITS', 25))

# --- 3. DATA FETCHING (API + FALLBACK) ---
def get_data(sym):
    # यहाँ आप अपनी InstitutionalDataEngine.fetch_live_option_chain डाल सकते हैं
    # अभी टेस्टिंग के लिए सिम्युलेटेड डेटा है ताकि हैंग न हो
    strikes = np.arange(24000, 25000, 50)
    df = pd.DataFrame({
        "Strike": strikes,
        "CE_OI": np.random.randint(100000, 900000, len(strikes)),
        "CE_LTP": np.random.uniform(50, 400, len(strikes)),
        "PE_LTP": np.random.uniform(50, 400, len(strikes)),
        "PE_OI": np.random.randint(100000, 900000, len(strikes))
    })
    return df, 24580.0

df, spot = get_data(selected_symbol)

# --- 4. ANALYTICS & DASHBOARD ---
st.markdown("---")
m1, m2, m3 = st.columns(3)
m1.metric("Live Spot", f"₹{spot:,.2f}")
m2.metric("Lot Size", auto_lot)
m3.metric("PCR", "1.09")
st.markdown("---")

# --- 5. CLEAN DATAFRAME ---
st.dataframe(df, use_container_width=True)

# --- 6. AUTO-REFRESH (Throttled) ---
if st.checkbox("Live Refresh (3s)"):
    time.sleep(3)
    st.rerun()
