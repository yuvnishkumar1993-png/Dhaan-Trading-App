import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime

# Page Config
st.set_page_config(page_title="Quant Terminal", layout="wide")

# Persistent Session Protection
if "client_id" not in st.session_state: st.session_state.client_id = ""
if "access_token" not in st.session_state: st.session_state.access_token = ""

# Data Engine (Optimized & Safe Cache)
@st.cache_data(ttl=3600)
def load_master_data():
    try:
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        df = pd.read_csv(url, low_memory=False)
        df.columns = [str(col).strip().upper() for col in df.columns]
        return df
    except: 
        return pd.DataFrame()

master_df = load_master_data()

st.title("⚡ Institutional Quant Terminal Pro - Backtest")

# --- 1. SAFE SMART ASSET & SCRIP SELECTOR ---
col1, col2 = st.columns(2)
with col1:
    asset_type = st.selectbox("Segment", ["Indices", "F&O Stocks"], key="bk_seg")

with col2:
    default_indices = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]
    default_stocks = ["RELIANCE", "TCS", "SBIN", "INFY", "HDFCBANK", "ICICIBANK", "TATAMOTORS"]
    
    # सुरक्षित कॉलम पहचान (Safe Column Mapping)
    seg_col = next((c for c in ['SEM_EXCH_SEGMENT', 'EXCH_SEGMENT', 'SEGMENT'] if c in master_df.columns), None)
    sym_col = next((c for c in ['SEM_TRADING_SYMBOL', 'TRADING_SYMBOL', 'SYMBOL'] if c in master_df.columns), None)
    
    syms = []
    if not master_df.empty and seg_col and sym_col:
        try:
            if asset_type == "Indices":
                sub_df = master_df[master_df[seg_col].astype(str).str.upper().isin(['IDX_I', 'BSE_IDX'])]
            else:
                sub_df = master_df[master_df[seg_col].astype(str).str.upper().isin(['NSE_EQ', 'BSE_EQ'])]
            syms = sub_df[sym_col].dropna().unique().tolist()
        except:
            syms = []
            
    if not syms:
        syms = default_indices if asset_type == "Indices" else default_stocks

    selected_symbol = st.selectbox("Search Symbol", options=syms, key="bk_sym")

# --- 2. AUTO-DETECT LOT SIZE & PARAMETERS SAFELY ---
auto_lot = 25
lot_col = next((c for c in ['SEM_LOT_UNITS', 'LOT_SIZE', 'LOT_UNITS'] if c in master_df.columns), None)

if not master_df.empty and sym_col and lot_col:
    match_row = master_df[master_df[sym_col] == str(selected_symbol).upper()]
    if not match_row.empty:
        val_lot = match_row.iloc[0].get(lot_col, auto_lot)
        if pd.notnull(val_lot) and int(val_lot) > 0:
            auto_lot = int(val_lot)
else:
    # डिफॉल्ट लॉट साइज मैप
    lot_map = {"NIFTY": 25, "BANKNIFTY": 15, "FINNIFTY": 25, "SENSEX": 10, "RELIANCE": 250, "TCS": 175, "SBIN": 750}
    auto_lot = lot_map.get(selected_symbol.upper(), 25)

# --- 3. DATA FETCHING (SIMULATED / BACKTEST ENGINE) ---
def get_backtest_data(sym):
    strikes = np.arange(24000, 25000, 50)
    df = pd.DataFrame({
        "Strike": strikes,
        "CE_OI": np.random.randint(100000, 900000, len(strikes)),
        "CE_LTP": np.random.uniform(50, 400, len(strikes)),
        "PE_LTP": np.random.uniform(50, 400, len(strikes)),
        "PE_OI": np.random.randint(100000, 900000, len(strikes))
    })
    return df, 24580.0

df, spot = get_backtest_data(selected_symbol)

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
if st.checkbox("Live Refresh (3s)", key="bk_refresh"):
    time.sleep(3)
    st.rerun()
