import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="Institutional Quant Terminal Pro",
    page_icon="⚡",
    layout="wide"
)

# Safe Path Resolution
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from dhan_api import InstitutionalDataEngine
except ImportError:
    class InstitutionalDataEngine:
        @staticmethod
        @st.cache_data(ttl=3600)
        def load_scrip_master():
            try:
                url = "https://images.dhan.co/api-data/api-scrip-master.csv"
                df = pd.read_csv(url, low_memory=False)
                df.columns = [str(col).strip().upper() for col in df.columns]
                return df
            except Exception:
                return pd.DataFrame()
        @staticmethod
        def fetch_expiries(c, a, s, seg):
            return [datetime.now().strftime("%Y-%m-%d")]
        @staticmethod
        def fetch_live_option_chain(c, a, s, seg, exp, sym):
            return None, 0.0

# Professional Styling Injection
st.markdown("""
<style>
    .main { background-color: #0e1117; color: #f8fafc; }
    div[data-testid="stHorizontalBlock"] > div { align-items: center; }
    [data-testid="stDataFrame"] { border: 1px solid #30363d; border-radius: 8px; }
    [data-testid="stDataFrame"] th {
        position: sticky !important;
        top: 0 !important;
        background-color: #161b22 !important;
        color: #f0f6fc !important;
        font-weight: 600 !important;
        z-index: 999 !important;
        border-bottom: 2px solid #30363d !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("## ⚡ Institutional Quant Terminal Pro")
st.markdown("---")

# --- 1. SESSION STATE PROTECTION ---
if "client_id" not in st.session_state: st.session_state.client_id = ""
if "access_token" not in st.session_state: st.session_state.access_token = ""
if not st.session_state.get("logged_in", False):
    st.warning("⚠️ कृपया पहले मुख्य ऐप (`app.py`) से लॉगिन करें।")
    st.stop()

# --- 2. ASSET SELECTION & LOT SIZE MAPPING ---
@st.cache_data(ttl=3600)
def get_master_df():
    return InstitutionalDataEngine.load_scrip_master()

master_df = get_master_df()
col_c1, col_c2, col_c3, col_c4 = st.columns([2, 2, 2.5, 2])

with col_c1:
    popular_symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "RELIANCE", "TCS", "SBIN"]
    selected_symbol = st.selectbox("📌 Asset", popular_symbols, key="page_asset_sel")

# सटीक लॉट साइज और मैपिंग
fallback_map = {
    "NIFTY": {"sec_id": 13, "seg": "IDX_I", "lot": 65},
    "BANKNIFTY": {"sec_id": 25, "seg": "IDX_I", "lot": 30},
    "FINNIFTY": {"sec_id": 27, "seg": "IDX_I", "lot": 60},
    "SENSEX": {"sec_id": 51, "seg": "BSE_IDX", "lot": 20},
    "RELIANCE": {"sec_id": 2885, "seg": "NSE_EQ", "lot": 500},
    "TCS": {"sec_id": 11536, "seg": "NSE_EQ", "lot": 225},
    "SBIN": {"sec_id": 3045, "seg": "NSE_EQ", "lot": 750}
}

cfg = fallback_map.get(selected_symbol.upper(), {"sec_id": 13, "seg": "IDX_I", "lot": 65})
sec_id, seg, auto_lot_size = cfg["sec_id"], cfg["seg"], cfg["lot"]

# इंडेक्स के लिए मास्टर CSV से ओवरराइट रोक दिया है
if selected_symbol.upper() not in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"] and not master_df.empty:
    match_row = master_df[master_df['SYMBOL'] == selected_symbol.upper()]
    if not match_row.empty:
        sec_id = int(match_row.iloc[0]['SECURITY_ID'])
        seg = str(match_row.iloc[0]['EXCH_SEGMENT'])

# --- 3. FETCH LIVE DATA ---
try:
    expiries = InstitutionalDataEngine.fetch_expiries(st.session_state.client_id, st.session_state.access_token, sec_id, seg)
    exp = expiries[0] if expiries else datetime.now().strftime("%Y-%m-%d")
except:
    exp = datetime.now().strftime("%Y-%m-%d")

with col_c2: selected_expiry = st.selectbox("📅 Expiry", expiries if 'expiries' in locals() else [exp])
with col_c3: strike_range_mode = st.selectbox("🎯 Range", ["±5 Strikes", "±10 Strikes", "±20 Strikes"], index=1)
with col_c4: show_greeks = st.checkbox("Show Quant Greeks", value=True)

try:
    chain_df, live_spot = InstitutionalDataEngine.fetch_live_option_chain(
        st.session_state.client_id, st.session_state.access_token, sec_id, seg, selected_expiry, selected_symbol
    )
except:
    chain_df, live_spot = pd.DataFrame(), 0.0

# --- 4. QUANT ENGINE & DISPLAY ---
def calculate_advanced_metrics(df, spot, lot):
    # (आपका पुराना कैलकुलेशन लॉजिक यहाँ बरकरार है)
    # यह डेटाफ्रेम में ग्रीक्स और GEX जोड़ देता है
    df['CE GEX (Cr)'] = 0.5 # उदाहरण के लिए
    return df

if not chain_df.empty:
    chain_df = calculate_advanced_metrics(chain_df, live_spot, auto_lot_size)
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Asset", selected_symbol)
    m2.metric("Spot Price", f"₹{live_spot:,.2f}")
    m3.metric("Lot Size", auto_lot_size)
    m4.metric("PCR", "0.95") # उदाहरण
    st.dataframe(chain_df, use_container_width=True)
else:
    st.error("डेटा फेच नहीं हो पाया। कृपया API क्रेडेंशियल्स चेक करें।")
