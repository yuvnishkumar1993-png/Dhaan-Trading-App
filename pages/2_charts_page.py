import os
import sys
import streamlit as st
import pandas as pd
import numpy as np

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Page Configuration
st.set_page_config(
    page_title="Mod A - Institutional OI Profile",
    page_icon="📊",
    layout="wide"
)

# Safe Path Resolution
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from dhan_api import InstitutionalDataEngine
except ImportError:
    st.error("❌ `dhan_api.py` module could not be imported. Please check root directory.")
    st.stop()

# Styling
st.markdown("""
<style>
    .main { background-color: #0b0e14; color: #f8fafc; }
    div[data-testid="stHorizontalBlock"] > div { align-items: center; }
</style>
""", unsafe_allow_html=True)

st.markdown("### 📊 Module A: Open Interest (OI) Profile — Support & Resistance")
st.markdown("---")

if "client_id" not in st.session_state: st.session_state.client_id = ""
if "access_token" not in st.session_state: st.session_state.access_token = ""

client_id = st.session_state.client_id
access_token = st.session_state.access_token

col_c1, col_c2 = st.columns(2)

with col_c1:
    default_symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "RELIANCE"]
    selected_symbol = st.selectbox("📌 Asset", default_symbols, key="mod_a_asset")

fallback_map = {
    "NIFTY": {"sec_id": 13, "seg": "IDX_I"},
    "BANKNIFTY": {"sec_id": 25, "seg": "IDX_I"},
    "FINNIFTY": {"sec_id": 27, "seg": "IDX_I"},
    "SENSEX": {"sec_id": 51, "seg": "BSE_IDX"},
    "RELIANCE": {"sec_id": 2885, "seg": "NSE_EQ"},
}
cfg = fallback_map.get(selected_symbol.upper(), {"sec_id": 13, "seg": "IDX_I"})
sec_id, seg = cfg["sec_id"], cfg["seg"]

try:
    expiries = InstitutionalDataEngine.fetch_expiries(client_id, access_token, sec_id, seg) or [datetime.now().strftime("%Y-%m-%d")]
except Exception:
    expiries = ["2026-08-11"]

with col_c2:
    selected_expiry = st.selectbox("📅 Expiry", expiries, key="mod_a_exp")

# --- FETCH REAL LIVE OPTION CHAIN ---
try:
    chain_df, live_spot = InstitutionalDataEngine.fetch_live_option_chain(
        client_id, access_token, sec_id, seg, selected_expiry, selected_symbol
    )
except Exception as e:
    st.error(f"⚠️ Live Data Fetch Error: {e}")
    chain_df, live_spot = pd.DataFrame(), 0.0

if chain_df is None or chain_df.empty or live_spot <= 0:
    st.warning(f"⚠️ **{selected_symbol}** के लिए लाइव ऑप्शन चेन डेटा प्राप्त नहीं हुआ। कृपया जाँच करें।")
    st.stop()

# --- BULLETPROOF COLUMN MAPPING & STRIKE SORTING ---
strike_col = next((c for c in chain_df.columns if 'STRIKE' in str(c).upper()), chain_df.columns[0])
chain_df['Strike'] = pd.to_numeric(chain_df[strike_col], errors='coerce')
chain_df.dropna(subset=['Strike'], inplace=True)

# Smart column mapping for Call and Put OI
for col in chain_df.columns:
    uc = str(col).upper()
    if ('CE' in uc or 'CALL' in uc) and ('OI' in uc) and 'CHG' not in uc:
        chain_df['Raw_CE_OI'] = pd.to_numeric(chain_df[col], errors='coerce').fillna(0)
    elif ('PE' in uc or 'PUT' in uc) and ('OI' in uc) and 'CHG' not in uc:
        chain_df['Raw_PE_OI'] = pd.to_numeric(chain_df[col], errors='coerce').fillna(0)

if 'Raw_CE_OI' not in chain_df.columns: chain_df['Raw_CE_OI'] = chain_df.get('CE_OI', 0)
if 'Raw_PE_OI' not in chain_df.columns: chain_df['Raw_PE_OI'] = chain_df.get('PE_OI', 0)

# ALWAYS SORT ASCENDING BY STRIKE
chain_df = chain_df.sort_values('Strike', ascending=True).reset_index(drop=True)

# Filter ±10 strikes around spot for clean display
chain_df['Dist'] = abs(chain_df['Strike'] - live_spot)
idx = chain_df['Dist'].idxmin()
disp_df = chain_df.iloc[max(0, idx-10):min(len(chain_df), idx+11)].copy()
disp_df = disp_df.sort_values('Strike', ascending=True).reset_index(drop=True)

strike_str_list = [str(int(s)) for s in disp_df['Strike']]

# Metrics Top Bar
m1, m2 = st.columns(2)
with m1: st.metric("Live Spot", f"₹{live_spot:,.1f}")
with m2: 
    f_ce = disp_df['Raw_CE_OI'].sum()
    f_pe = disp_df['Raw_PE_OI'].sum()
    pcr = round(f_pe / f_ce, 2) if f_ce > 0 else 0
    st.metric("OI PCR", pcr)

st.markdown("---")

# --- PLOTLY CHART FOR MOD A ---
fig = go.Figure()
fig.add_trace(go.Bar(x=strike_str_list, y=disp_df['Raw_CE_OI'], name='CE OI (Resistance)', marker_color='#ef4444'))
fig.add_trace(go.Bar(x=strike_str_list, y=disp_df['Raw_PE_OI'], name='PE OI (Support)', marker_color='#22c55e'))

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15, 23, 42, 0.8)",
    font=dict(color="#f8fafc", size=11, family="Inter, sans-serif"),
    hovermode="x unified",
    margin=dict(l=15, r=15, t=35, b=15),
    legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
    height=360,
    barmode="group",
    xaxis=dict(type='category', tickangle=-30, title="Strike Price"),
    yaxis=dict(title="Open Interest")
)

st.plotly_chart(fig, use_container_width=True)

max_ce = disp_df.loc[disp_df['Raw_CE_OI'].idxmax()]['Strike'] if not disp_df.empty else 0
max_pe = disp_df.loc[disp_df['Raw_PE_OI'].idxmax()]['Strike'] if not disp_df.empty else 0
st.success(f"💡 **Module A Analysis:** Major Resistance (Highest Call OI) is at **{max_ce}** | Major Support (Highest Put OI) is at **{max_pe}**.")
