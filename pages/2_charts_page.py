import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Page Configuration
st.set_page_config(
    page_title="Mod A - Advanced OI Profile & Sigma Bands",
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
    st.error("❌ `dhan_api.py` module could not be imported.")
    st.stop()

# Styling
st.markdown("""
<style>
    .main { background-color: #0b0e14; color: #f8fafc; }
    div[data-testid="stHorizontalBlock"] > div { align-items: center; }
</style>
""", unsafe_allow_html=True)

st.markdown("### 📊 Module A: Institutional OI Profile — Sigma Bands, Max Pain & Volume Analytics")
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
    st.warning(f"⚠️ **{selected_symbol}** के लिए लाइव ऑप्शन चेन डेटा प्राप्त नहीं हुआ।")
    st.stop()

# --- BULLETPROOF COLUMN MAPPING & STRIKE SORTING ---
strike_col = next((c for c in chain_df.columns if 'STRIKE' in str(c).upper()), chain_df.columns[0])
chain_df['Strike'] = pd.to_numeric(chain_df[strike_col], errors='coerce')
chain_df.dropna(subset=['Strike'], inplace=True)

# Smart column mapping for OI, Volume and IV
for col in chain_df.columns:
    uc = str(col).upper()
    if ('CE' in uc or 'CALL' in uc) and ('OI' in uc) and 'CHG' not in uc:
        chain_df['Raw_CE_OI'] = pd.to_numeric(chain_df[col], errors='coerce').fillna(0)
    elif ('PE' in uc or 'PUT' in uc) and ('OI' in uc) and 'CHG' not in uc:
        chain_df['Raw_PE_OI'] = pd.to_numeric(chain_df[col], errors='coerce').fillna(0)
    elif ('CE' in uc or 'CALL' in uc) and 'VOL' in uc:
        chain_df['CE_Volume'] = pd.to_numeric(chain_df[col], errors='coerce').fillna(0)
    elif ('PE' in uc or 'PUT' in uc) and 'VOL' in uc:
        chain_df['PE_Volume'] = pd.to_numeric(chain_df[col], errors='coerce').fillna(0)
    elif ('CE' in uc or 'CALL' in uc) and 'IV' in uc:
        chain_df['CE_IV'] = pd.to_numeric(chain_df[col], errors='coerce').fillna(13.0)
    elif ('PE' in uc or 'PUT' in uc) and 'IV' in uc:
        chain_df['PE_IV'] = pd.to_numeric(chain_df[col], errors='coerce').fillna(13.5)

if 'Raw_CE_OI' not in chain_df.columns: chain_df['Raw_CE_OI'] = 0
if 'Raw_PE_OI' not in chain_df.columns: chain_df['Raw_PE_OI'] = 0
if 'CE_Volume' not in chain_df.columns: chain_df['CE_Volume'] = 100000
if 'PE_Volume' not in chain_df.columns: chain_df['PE_Volume'] = 100000
if 'CE_IV' not in chain_df.columns: chain_df['CE_IV'] = 13.0
if 'PE_IV' not in chain_df.columns: chain_df['PE_IV'] = 13.5

# ALWAYS SORT ASCENDING BY STRIKE
chain_df = chain_df.sort_values('Strike', ascending=True).reset_index(drop=True)

# Filter ±12 strikes around spot for clean display
chain_df['Dist'] = abs(chain_df['Strike'] - live_spot)
idx = chain_df['Dist'].idxmin()
disp_df = chain_df.iloc[max(0, idx-12):min(len(chain_df), idx+13)].copy()
disp_df = disp_df.sort_values('Strike', ascending=True).reset_index(drop=True)

strike_str_list = [str(int(s)) for s in disp_df['Strike']]

# --- CALCULATE QUANT METRICS (MAX PAIN & SIGMA BANDS) ---
def calculate_max_pain(df, spot):
    strikes, ce_oi, pe_oi = df['Strike'].values, df['Raw_CE_OI'].values, df['Raw_PE_OI'].values
    min_payout, max_pain_strike = float('inf'), strikes[0]
    for exp_price in strikes:
        payout = sum((exp_price - K) * ce_oi[i] if exp_price > K else (K - exp_price) * pe_oi[i] for i, K in enumerate(strikes))
        if payout < min_payout: min_payout, max_pain_strike = payout, exp_price
    return int(max_pain_strike)

max_pain_val = calculate_max_pain(chain_df, live_spot)

# Expected Move / Sigma Calculation based on ATM IV
atm_row = chain_df.loc[chain_df['Dist'].idxmin()]
atm_iv = (atm_row.get('CE_IV', 13.0) + atm_row.get('PE_IV', 13.5)) / 2.0 / 100.0
days_to_exp = 3.0 / 365.0
sigma_1 = live_spot * atm_iv * math.sqrt(days_to_exp)
sigma_2 = sigma_1 * 2.0

upper_1sig, lower_1sig = live_spot + sigma_1, live_spot - sigma_1
upper_2sig, lower_2sig = live_spot + sigma_2, live_spot - sigma_2

# Total Volume Totals
total_call_vol = int(disp_df['CE_Volume'].sum())
total_put_vol = int(disp_df['PE_Volume'].sum())
total_call_oi = int(disp_df['Raw_CE_OI'].sum())
total_put_oi = int(disp_df['Raw_PE_OI'].sum())
pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0

# Metrics Top Bar
m1, m2, m3, m4, m5 = st.columns(5)
with m1: st.metric("Live Spot", f"₹{live_spot:,.1f}")
with m2: st.metric("Max Pain", max_pain_val)
with m3: st.metric("OI PCR", pcr)
with m4: st.metric("Total Call Vol", f"{total_call_vol:,}")
with m5: st.metric("Total Put Vol", f"{total_put_vol:,}")

st.markdown("---")

closest_spot_strike = str(int(min(disp_df['Strike'], key=lambda x: abs(x - live_spot))))
closest_pain_strike = str(int(min(disp_df['Strike'], key=lambda x: abs(x - max_pain_val))))

# --- PLOTLY CHART FOR MOD A WITH SAFE SHAPES ---
fig = go.Figure()
fig.add_trace(go.Bar(x=strike_str_list, y=disp_df['Raw_CE_OI'], name='CE OI (Resistance)', marker_color='#ef4444'))
fig.add_trace(go.Bar(x=strike_str_list, y=disp_df['Raw_PE_OI'], name='PE OI (Support)', marker_color='#22c55e'))

# Safely add vertical indicator lines using shapes and annotations instead of add_vline
fig.add_shape(type="line", x0=closest_spot_strike, x1=closest_spot_strike, y0=0, y1=1, yref="paper", line=dict(color="#38bdf8", dash="dash", width=2))
fig.add_annotation(x=closest_spot_strike, y=1, yref="paper", text=f"Spot: {live_spot:.1f}", showarrow=False, yanchor="bottom", font=dict(color="#38bdf8", size=10))

fig.add_shape(type="line", x0=closest_pain_strike, x1=closest_pain_strike, y0=0, y1=1, yref="paper", line=dict(color="#f43f5e", dash="dot", width=2))
fig.add_annotation(x=closest_pain_strike, y=0.9, yref="paper", text=f"Max Pain: {max_pain_val}", showarrow=False, yanchor="bottom", font=dict(color="#f43f5e", size=10))

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15, 23, 42, 0.8)",
    font=dict(color="#f8fafc", size=11, family="Inter, sans-serif"),
    hovermode="x unified",
    margin=dict(l=15, r=15, t=35, b=15),
    legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
    height=380,
    barmode="group",
    xaxis=dict(type='category', tickangle=-30, title="Strike Price"),
    yaxis=dict(title="Open Interest")
)

st.plotly_chart(fig, use_container_width=True)

max_ce = disp_df.loc[disp_df['Raw_CE_OI'].idxmax()]['Strike'] if not disp_df.empty else 0
max_pe = disp_df.loc[disp_df['Raw_PE_OI'].idxmax()]['Strike'] if not disp_df.empty else 0

st.success(f"""
💡 **Module A Quantitative Breakdown:**
- **Major Resistance (Max Call OI):** {max_ce} | **Major Support (Max Put OI):** {max_pe}
- **Max Pain Magnet:** {max_pain_val} (Target settlement zone)
- **Expected Sigma Range ($\pm 1\sigma$):** {lower_1sig:,.1f} to {upper_1sig:,.1f}
- **Volume Balance:** Total Call Vol: {total_call_vol:,} vs Total Put Vol: {total_put_vol:,}
""")
