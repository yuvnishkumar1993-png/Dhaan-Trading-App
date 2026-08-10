import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Institutional Quant Terminal", page_icon="⚡", layout="wide")

# Safe Path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path: sys.path.append(ROOT_DIR)

try:
    from dhan_api import InstitutionalDataEngine
except ImportError:
    # (आपका वही पिछला क्लास स्ट्रक्चर यहाँ रहेगा)
    pass

st.markdown("## ⚡ Institutional Quant Terminal Pro")

# --- 1. SESSION PROTECTION ---
if not st.session_state.get("logged_in", False):
    st.warning("⚠️ कृपया पहले मुख्य ऐप से लॉगिन करें।")
    st.stop()

# --- 2. ASSET MAPPING (अचूक मैपिंग) ---
# यहाँ हम इंडेक्स के लिए फिक्स आईडी और स्टॉक के लिए मास्टर डेटा का उपयोग करेंगे
fallback_map = {
    "NIFTY": {"sec_id": 13, "seg": "IDX_I", "lot": 65},
    "BANKNIFTY": {"sec_id": 25, "seg": "IDX_I", "lot": 30},
    "FINNIFTY": {"sec_id": 27, "seg": "IDX_I", "lot": 60},
    "SENSEX": {"sec_id": 51, "seg": "BSE_IDX", "lot": 20},
    "RELIANCE": {"sec_id": 2885, "seg": "NSE_EQ", "lot": 500},
    "TCS": {"sec_id": 11536, "seg": "NSE_EQ", "lot": 225},
    "SBIN": {"sec_id": 3045, "seg": "NSE_EQ", "lot": 750}
}

selected_symbol = st.selectbox("📌 Asset", list(fallback_map.keys()), key="page_asset_sel")

# मैपिंग लॉजिक
if selected_symbol in fallback_map:
    cfg = fallback_map[selected_symbol]
    sec_id, seg, auto_lot_size = cfg["sec_id"], cfg["seg"], cfg["lot"]
else:
    # यदि स्टॉक है, तो मास्टर फाइल से ढूंढें (सिर्फ यहाँ मास्टर CSV काम करेगी)
    master_df = InstitutionalDataEngine.load_scrip_master()
    match = master_df[master_df['SYMBOL'] == selected_symbol.upper()]
    sec_id = int(match.iloc[0]['SECURITY_ID']) if not match.empty else 13
    seg = str(match.iloc[0]['EXCH_SEGMENT']) if not match.empty else "IDX_I"
    auto_lot_size = 50 # स्टॉक के लिए डिफ़ॉल्ट

# --- 3. API CALL ---
try:
    expiries = InstitutionalDataEngine.fetch_expiries(st.session_state.client_id, st.session_state.access_token, sec_id, seg)
    exp = expiries[0] if expiries else datetime.now().strftime("%Y-%m-%d")
    selected_expiry = st.selectbox("📅 Expiry", expiries)
    
    chain_df, live_spot = InstitutionalDataEngine.fetch_live_option_chain(
        st.session_state.client_id, st.session_state.access_token, sec_id, seg, selected_expiry, selected_symbol
    )
except Exception as e:
    st.error(f"API Error: {e}")
    chain_df, live_spot = pd.DataFrame(), 0.0

# --- 4. DATA VALIDATION ---
if chain_df is not None and not chain_df.empty and live_spot > 0:
    # (कैलकुलेशन और डिस्प्ले वाला हिस्सा यहाँ जोड़ें...)
    st.success(f"{selected_symbol} का लाइव डेटा सफलतापूर्वक लोड हुआ!")
    st.metric("Live Spot", f"₹{live_spot:,.2f}")
else:
    st.error("डेटा नहीं मिल रहा! क्या API टोकन एक्सपायर हो गया है?")
