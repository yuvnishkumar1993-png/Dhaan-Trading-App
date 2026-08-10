import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime
import plotly.graph_objects as go

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
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    class InstitutionalDataEngine:
        @staticmethod
        def load_scrip_master():
            return pd.DataFrame()
        @staticmethod
        def fetch_expiries(c, a, s, seg):
            return [datetime.now().strftime("%Y-%m-%d")]
        @staticmethod
        def fetch_live_option_chain(c, a, s, seg, exp, sym):
            # यह केवल तब चलेगा जब dhan_api फाइल नहीं होगी (सिमुलेशन)
            spot = 24583.80
            strikes = np.arange(24000, 25200, 50)
            recs = []
            for st_val in strikes:
                recs.append({
                    "Strike": int(st_val),
                    "Raw_CE_OI": np.random.randint(500000, 2000000), "CE_Chg_OI": np.random.randint(-20000, 50000), "CE_IV": 13.0, "CE_LTP": max(1.0, spot - st_val + 20),
                    "PE_LTP": max(1.0, st_val - spot + 20), "PE_IV": 13.5, "CE_Chg_OI": np.random.randint(-20000, 50000), "Raw_PE_OI": np.random.randint(500000, 2000000)
                })
            return pd.DataFrame(recs), spot

# Professional Styling Injection
st.markdown("""
<style>
    .main { background-color: #0e1117; color: #f8fafc; }
    div[data-testid="stHorizontalBlock"] > div { align-items: center; }
    [data-testid="stDataFrame"] { border: 1px solid #30363d; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown("## ⚡ Institutional Quant Terminal Pro (Debug Version)")
st.markdown("---")

if not API_AVAILABLE:
    st.warning("⚠️ **Simulation Mode Active:** `dhan_api.py` not found. Calculations are running on mock data.")

# Session State Check
if "client_id" not in st.session_state:
    st.session_state.client_id = ""
if "access_token" not in st.session_state:
    st.session_state.access_token = ""

client_id = st.session_state.client_id
access_token = st.session_state.access_token

# --- GLOBAL CONTROLS ---
col_h1, col_h2, col_h3, col_h4 = st.columns([2, 2, 2, 2])

with col_h1:
    selected_symbol = st.selectbox("📌 Asset", ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "RELIANCE"], key="global_asset_sel")

master_dict = {
    "NIFTY": {"sec_id": 13, "seg": "IDX_I", "lot": 65},
    "BANKNIFTY": {"sec_id": 25, "seg": "IDX_I", "lot": 15},
    "FINNIFTY": {"sec_id": 27, "seg": "IDX_I", "lot": 25},
    "SENSEX": {"sec_id": 51, "seg": "BSE_IDX", "lot": 10},
    "RELIANCE": {"sec_id": 2885, "seg": "NSE_EQ", "lot": 250}
}
cfg = master_dict.get(selected_symbol.upper(), {"sec_id": 13, "seg": "IDX_I", "lot": 65})
sec_id, seg, server_lot = cfg["sec_id"], cfg["seg"], cfg["lot"]

try:
    expiries = InstitutionalDataEngine.fetch_expiries(client_id, access_token, sec_id, seg)
    if not expiries: expiries = [datetime.now().strftime("%Y-%m-%d")]
except Exception:
    expiries = [datetime.now().strftime("%Y-%m-%d")]

with col_h2:
    selected_expiry = st.selectbox("📅 Expiry", expiries, index=0)

with col_h3:
    active_page = st.selectbox("📑 Terminal Page", ["Page 1: Option Chain", "Page 2: Sensibull Analytics & Graphs"])

with col_h4:
    lot_size = st.number_input("⚙️ Lot Size", min_value=1, value=int(server_lot))

# --- FETCH DATA ---
try:
    chain_df, live_spot = InstitutionalDataEngine.fetch_live_option_chain(
        client_id, access_token, sec_id, seg, selected_expiry, selected_symbol
    )
except Exception as e:
    st.error(f"API Error: {e}")
    chain_df, live_spot = pd.DataFrame(), 24583.80

if chain_df is None or chain_df.empty:
    spot_val = 24583.80
    strikes = np.arange(24000, 25200, 50)
    recs = [{"Strike": int(st), "Raw_CE_OI": 1000000, "Raw_PE_OI": 1200000, "CE_LTP": 50, "PE_LTP": 50, "CE_IV": 13, "PE_IV": 13} for st in strikes]
    chain_df, live_spot = pd.DataFrame(recs), spot_val

# --- STRICT NORMALIZATION & TYPECASTING (डेटा को सटीक बनाने का नियम) ---
def clean_and_normalize(df):
    df.columns = [str(c).strip() for c in df.columns]
    
    # Strike mapping
    for col in ['Strike', 'STRIKE', 'strike_price', 'strike']:
        if col in df.columns:
            df['Strike'] = pd.to_numeric(df[col], errors='coerce')
            break
    if 'Strike' not in df.columns:
        df['Strike'] = pd.to_numeric(df.iloc[:, 0], errors='coerce')
        
    df.dropna(subset=['Strike'], inplace=True)
    df.sort_values('Strike', inplace=True)

    # Numeric conversion for critical calculation columns
    numeric_fields = ['Raw_CE_OI', 'Raw_PE_OI', 'CE_LTP', 'PE_LTP', 'CE_IV', 'PE_IV', 'CE_Chg_OI', 'PE_Chg_OI']
    for field in numeric_fields:
        if field not in df.columns:
            # वैकल्पिक नाम तलाशना
            alt_found = False
            for alt in [field.lower(), field.upper(), field.replace("Raw_", ""), field.replace("_", "")]:
                for c in df.columns:
                    if alt in c.lower():
                        df[field] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                        alt_found = True
                        break
                if alt_found: break
            if not alt_found:
                df[field] = 100000 if 'OI' in field else (10.0 if 'IV' in field else 50.0)
        else:
            df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0)
            
    return df

chain_df = clean_and_normalize(chain_df)

# ==========================================
# PAGE 2: SENSIBULL GRAPHS WITH CORRECT MATH
# ==========================================
if "Page 2" in active_page:
    st.markdown("### 🎯 Page 2: Advanced OI & Analytics Graphs")
    st.markdown("---")
    
    # Corrected Calculations
    total_call_oi = chain_df['Raw_CE_OI'].sum()
    total_put_oi = chain_df['Raw_PE_OI'].sum()
    pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0
    
    # Accurate Max Pain Logic
    pain_dict = {}
    strikes = chain_df['Strike'].values
    ce_ois = chain_df['Raw_CE_OI'].values
    pe_ois = chain_df['Raw_PE_OI'].values
    
    for expiry_price in strikes:
        call_pain = np.maximum(0, expiry_price - strikes) * ce_ois
        put_pain = np.maximum(0, strikes - expiry_price) * pe_ois
        pain_dict[expiry_price] = (call_pain + put_pain).sum()
        
    max_pain_strike = min(pain_dict, key=pain_dict.get) if pain_dict else live_spot

    max_call_row = chain_df.loc[chain_df['Raw_CE_OI'].idxmax()] if not chain_df.empty else None
    max_put_row = chain_df.loc[chain_df['Raw_PE_OI'].idxmax()] if not chain_df.empty else None
    
    immediate_resistance = int(max_call_row['Strike']) if max_call_row is not None else 0
    immediate_support = int(max_put_row['Strike']) if max_put_row is not None else 0

    # KPI Metrics Bar
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Live PCR", pcr, delta="Bullish" if pcr > 1.1 else "Bearish")
    with m2: st.metric("Max Pain Strike", f"{max_pain_strike:,}")
    with m3: st.metric("Immediate Resistance", f"{immediate_resistance:,}", delta="Max Call OI")
    with m4: st.metric("Immediate Support", f"{immediate_support:,}", delta="Max Put OI")
    
    st.markdown("---")
    
    # Filter nearby strikes for crisp charts (±12 strikes)
    chain_df['Dist'] = abs(chain_df['Strike'] - live_spot)
    center_idx = chain_df['Dist'].idxmin()
    plot_df = chain_df.iloc[max(0, center_idx-12):min(len(chain_df), center_idx+13)].copy()

    # --- GRAPH 1: Sensibull Style OI Distribution ---
    st.markdown("#### 📊 Strike-wise Open Interest (OI) Distribution")
    fig_oi = go.Figure()
    fig_oi.add_trace(go.Bar(
        x=plot_df['Strike'], y=plot_df['Raw_CE_OI'] / 100000,
        name='Call OI (Resistance)', marker_color='#ef4444'
    ))
    fig_oi.add_trace(go.Bar(
        x=plot_df['Strike'], y=plot_df['Raw_PE_OI'] / 100000,
        name='Put OI (Support)', marker_color='#22c55e'
    ))
    fig_oi.add_vline(x=live_spot, line_dash="dash", line_color="#fbbf24", annotation_text=f"Spot: {live_spot:.1f}")
    fig_oi.update_layout(barmode='group', template='plotly_dark', xaxis_title="Strike", yaxis_title="OI (Lakhs)", height=400)
    st.plotly_chart(fig_oi, use_container_width=True)

    # --- GRAPH 2: IV Smile Chart ---
    st.markdown("#### 📉 Implied Volatility (IV) Smile")
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=plot_df['Strike'], y=plot_df['CE_IV'], mode='lines+markers', name='Call IV', line=dict(color='#ef4444')))
    fig_iv.add_trace(go.Scatter(x=plot_df['Strike'], y=plot_df['PE_IV'], mode='lines+markers', name='Put IV', line=dict(color='#22c55e')))
    fig_iv.add_vline(x=live_spot, line_dash="dash", line_color="#fbbf24")
    fig_iv.update_layout(template='plotly_dark', xaxis_title="Strike", yaxis_title="IV (%)", height=350)
    st.plotly_chart(fig_iv, use_container_width=True)

else:
    st.markdown("### 📊 Page 1: Option Chain View")
    st.dataframe(chain_df[['Strike', 'Raw_CE_OI', 'CE_LTP', 'PE_LTP', 'Raw_PE_OI']], use_container_width=True)

# --- DEBUG INSPECTOR (यह देखने के लिए कि असल डेटा क्या आ रहा है) ---
with st.expander("🛠️ Debug Inspector (Check Raw Columns & Values)"):
    st.write("Live Spot Price:", live_spot)
    st.write("Detected Columns:", chain_df.columns.tolist())
    st.dataframe(chain_df.head(10))
