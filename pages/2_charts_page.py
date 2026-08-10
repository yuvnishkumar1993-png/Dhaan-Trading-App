import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

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
            spot = 24583.80
            strikes = np.arange(24000, 25200, 50)
            recs = []
            for st_val in strikes:
                recs.append({
                    "Strike": int(st_val),
                    "CE_OI": np.random.randint(100000, 2000000), "CE_Chg_OI": np.random.randint(-50000, 150000), "CE_Volume": 1000000, "CE_IV": 13.0, "CE_LTP": max(1.0, spot - st_val + 20),
                    "PE_LTP": max(1.0, st_val - spot + 20), "PE_IV": 13.5, "PE_Volume": 1000000, "PE_Chg_OI": np.random.randint(-50000, 150000), "PE_OI": np.random.randint(100000, 2000000)
                })
            return pd.DataFrame(recs), spot

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

if not API_AVAILABLE:
    st.warning("⚠️ Warning: `dhan_api.py` not found. Running on simulation mode.")

# Session State Check
if "client_id" not in st.session_state:
    st.session_state.client_id = ""
if "access_token" not in st.session_state:
    st.session_state.access_token = ""

client_id = st.session_state.client_id
access_token = st.session_state.access_token

# --- GLOBAL HEADER CONTROLS ---
col_h1, col_h2, col_h3, col_h4 = st.columns([2, 2, 2, 2])

with col_h1:
    all_symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "RELIANCE", "TCS", "SBIN"]
    current_idx = all_symbols.index(st.session_state.get("global_symbol", "NIFTY")) if st.session_state.get("global_symbol", "NIFTY") in all_symbols else 0
    selected_symbol = st.selectbox("📌 Asset", all_symbols, index=current_idx, key="global_asset_sel")
    st.session_state.global_symbol = selected_symbol

master_dict = {
    "NIFTY": {"sec_id": 13, "seg": "IDX_I", "lot": 65},
    "BANKNIFTY": {"sec_id": 25, "seg": "IDX_I", "lot": 15},
    "FINNIFTY": {"sec_id": 27, "seg": "IDX_I", "lot": 25},
    "SENSEX": {"sec_id": 51, "seg": "BSE_IDX", "lot": 10},
    "RELIANCE": {"sec_id": 2885, "seg": "NSE_EQ", "lot": 250},
    "TCS": {"sec_id": 11536, "seg": "NSE_EQ", "lot": 175},
    "SBIN": {"sec_id": 3045, "seg": "NSE_EQ", "lot": 750}
}
cfg = master_dict.get(selected_symbol.upper(), {"sec_id": 13, "seg": "IDX_I", "lot": 65})
sec_id, seg, server_lot = cfg["sec_id"], cfg["seg"], cfg["lot"]

try:
    expiries = InstitutionalDataEngine.fetch_expiries(client_id, access_token, sec_id, seg)
    if not expiries:
        expiries = [datetime.now().strftime("%Y-%m-%d")]
except Exception:
    expiries = [datetime.now().strftime("%Y-%m-%d")]

with col_h2:
    selected_expiry = st.selectbox("📅 Expiry", expiries, index=0, key=f"exp_{selected_symbol}")

with col_h3:
    active_page = st.selectbox("📑 Terminal Page", ["Page 1: Core Option Chain", "Page 2: Sensibull-Style OI & Analytics Dashboard"])

with col_h4:
    lot_size = st.number_input("⚙️ Lot Size", min_value=1, max_value=10000, value=int(server_lot), step=1)

# --- FETCH LIVE DATA ---
try:
    chain_df, live_spot = InstitutionalDataEngine.fetch_live_option_chain(
        client_id, access_token, sec_id, seg, selected_expiry, selected_symbol
    )
except Exception as e:
    st.error(f"Error fetching live data: {e}")
    chain_df = pd.DataFrame()
    live_spot = 24583.80

if chain_df is None or chain_df.empty:
    spot_val = 24583.80
    strikes = np.arange(24000, 25200, 50)
    recs = []
    for st_val in strikes:
        recs.append({
            "Strike": int(st_val),
            "CE_OI": np.random.randint(100000, 2000000), "CE_Chg_OI": np.random.randint(-50000, 150000), "CE_Volume": 1000000, "CE_IV": 13.0, "CE_LTP": max(1.0, spot_val - st_val + 20),
            "PE_LTP": max(1.0, st_val - spot_val + 20), "PE_IV": 13.5, "PE_Volume": 1000000, "PE_Chg_OI": np.random.randint(-50000, 150000), "PE_OI": np.random.randint(100000, 2000000)
        })
    chain_df = pd.DataFrame(recs)
    live_spot = spot_val

# --- NORMALIZATION ENGINE ---
def normalize_option_chain_data(df):
    if df.empty:
        return df
    df.columns = [str(c).strip() for c in df.columns]
    
    strike_candidates = ['Strike', 'STRIKE', 'strike_price', 'StrikePrice', 'strike']
    for sc in strike_candidates:
        if sc in df.columns:
            df['Strike'] = pd.to_numeric(df[sc], errors='coerce')
            break
    if 'Strike' not in df.columns:
        df['Strike'] = df.iloc[:, 0]
    df.dropna(subset=['Strike'], inplace=True)
    df['STRIKE'] = df['Strike']

    for target, candidates in [
        ('CE_LTP', ['CE_LTP', 'Call_LTP', 'call_ltp']),
        ('PE_LTP', ['PE_LTP', 'Put_LTP', 'put_ltp']),
        ('Raw_CE_OI', ['Raw_CE_OI', 'CE_OI', 'Call_OI', 'call_oi']),
        ('Raw_PE_OI', ['Raw_PE_OI', 'PE_OI', 'Put_OI', 'put_oi']),
        ('CE_Chg_OI', ['CE_Chg_OI', 'Call_Chg_OI', 'ce_chg_oi']),
        ('PE_Chg_OI', ['PE_Chg_OI', 'Put_Chg_OI', 'pe_chg_oi']),
        ('CE_IV', ['CE_IV', 'Call_IV', 'ce_iv']),
        ('PE_IV', ['PE_IV', 'Put_IV', 'pe_iv'])
    ]:
        if target not in df.columns:
            for cand in candidates:
                if cand in df.columns:
                    df[target] = pd.to_numeric(df[cand], errors='coerce').fillna(0)
                    break
            if target not in df.columns:
                df[target] = 10.0 if 'IV' in target else 100000
    return df

chain_df = normalize_option_chain_data(chain_df)

# ==========================================
# PAGE 1: CORE OPTION CHAIN & PRICE ACTION
# ==========================================
if "Page 1" in active_page:
    st.markdown("### 📊 Page 1: Core Option Chain & Price Action Matrix")
    st.markdown("---")
    
    col_r1, col_r2 = st.columns([2, 2])
    with col_r1:
        strike_range_mode = st.selectbox("🎯 Strike Range", ["±5 Strikes", "±10 Strikes", "±20 Strikes", "Full Chain (All)"], index=1)
    with col_r2:
        show_greeks = st.checkbox("Show Quant Greeks & GEX", value=True)

    chain_df['Dist'] = abs(chain_df['Strike'] - live_spot)
    if "±5" in strike_range_mode:
        center_idx = chain_df['Dist'].idxmin()
        disp_df = chain_df.iloc[max(0, center_idx-5):min(len(chain_df), center_idx+6)].copy()
    elif "±10" in strike_range_mode:
        center_idx = chain_df['Dist'].idxmin()
        disp_df = chain_df.iloc[max(0, center_idx-10):min(len(chain_df), center_idx+11)].copy()
    elif "±20" in strike_range_mode:
        center_idx = chain_df['Dist'].idxmin()
        disp_df = chain_df.iloc[max(0, center_idx-20):min(len(chain_df), center_idx+21)].copy()
    else:
        disp_df = chain_df.copy()

    disp_df['CE OI (L)'] = round(disp_df['Raw_CE_OI'] / 100000, 2)
    disp_df['PE OI (L)'] = round(disp_df['Raw_PE_OI'] / 100000, 2)
    disp_df['CE Vol (M)'] = round(disp_df.get('CE_Volume', 100000) / 1000000, 2)
    disp_df['PE Vol (M)'] = round(disp_df.get('PE_Volume', 100000) / 1000000, 2)

    matrix_cols = ["CE Vol (M)", "CE_Chg_OI", "CE OI (L)", "CE_LTP", "STRIKE", "PE_LTP", "PE OI (L)", "PE_Chg_OI", "PE Vol (M)"]
    final_cols = [c for c in matrix_cols if c in disp_df.columns]
    matrix_df = disp_df[final_cols].copy()
    
    def style_page1(row):
        strike = row['STRIKE']
        styles = [''] * len(row)
        is_atm = abs(strike - live_spot) <= 25
        for i, col_name in enumerate(row.index):
            if col_name == 'STRIKE':
                styles[i] = 'background-color: #d97706; color: #ffffff; font-weight: bold; font-size: 15px;' if is_atm else 'background-color: #1f2937; color: #f9fafb;'
            elif 'CE' in col_name:
                styles[i] = 'background-color: #111e38; color: #e2e8f0;' if strike < live_spot else 'background-color: #0f172a; color: #94a3b8;'
            elif 'PE' in col_name:
                styles[i] = 'background-color: #381116; color: #e2e8f0;' if strike > live_spot else 'background-color: #1e1114; color: #94a3b8;'
        return styles

    st.dataframe(matrix_df.style.apply(style_page1, axis=1), use_container_width=True, height=600, hide_index=True)


# ========================================================
# PAGE 2: SENSIBULL-STYLE ADVANCED GRAPH DASHBOARD
# ========================================================
elif "Page 2" in active_page:
    st.markdown("### 🎯 Page 2: Sensibull-Style Advanced OI & Analytics Graphs")
    st.markdown("---")
    
    total_call_oi = chain_df['Raw_CE_OI'].sum()
    total_put_oi = chain_df['Raw_PE_OI'].sum()
    pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0
    
    # Max Pain Calculation
    pain_dict = {}
    strikes = chain_df['Strike'].values
    for strike in strikes:
        call_pain = np.maximum(0, strike - strikes) * chain_df['Raw_CE_OI'].values
        put_pain = np.maximum(0, strikes - strike) * chain_df['Raw_PE_OI'].values
        pain_dict[strike] = (call_pain + put_pain).sum()
    max_pain_strike = min(pain_dict, key=pain_dict.get) if pain_dict else live_spot

    max_call_row = chain_df.loc[chain_df['Raw_CE_OI'].idxmax()] if not chain_df.empty else None
    max_put_row = chain_df.loc[chain_df['Raw_PE_OI'].idxmax()] if not chain_df.empty else None
    
    immediate_resistance = int(max_call_row['Strike']) if max_call_row is not None else 0
    immediate_support = int(max_put_row['Strike']) if max_put_row is not None else 0

    # Top Macro KPI Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Live PCR", pcr, delta="Bullish" if pcr > 1.1 else "Bearish")
    with m2: st.metric("Max Pain Strike", f"{max_pain_strike:,}")
    with m3: st.metric("Immediate Resistance", f"{immediate_resistance:,}", delta="Max Call OI")
    with m4: st.metric("Immediate Support", f"{immediate_support:,}", delta="Max Put OI")
    
    st.markdown("---")
    
    # Filter nearby strikes for crisp plotting (±15 strikes around spot)
    chain_df['Dist'] = abs(chain_df['Strike'] - live_spot)
    center_idx = chain_df['Dist'].idxmin()
    plot_df = chain_df.iloc[max(0, center_idx-15):min(len(chain_df), center_idx+16)].copy()

    # --- CHART 1: Sensibull-Style Open Interest Distribution Bar Chart ---
    st.markdown("#### 📊 1. Strike-wise Open Interest (OI) Distribution Chart")
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
    fig_oi.update_layout(
        barmode='group', template='plotly_dark',
        xaxis_title="Strike Price", yaxis_title="Open Interest (in Lakhs)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=450
    )
    st.plotly_chart(fig_oi, use_container_width=True)

    st.markdown("---")

    # --- CHART 2: Intraday Change in OI (Buildup Analysis) ---
    st.markdown("#### ⚡ 2. Intraday Change in OI ($\Delta OI$) Buildup Chart")
    fig_chg = go.Figure()
    fig_chg.add_trace(go.Bar(
        x=plot_df['Strike'], y=plot_df['CE_Chg_OI'],
        name='Call Chg in OI', marker_color='#f87171'
    ))
    fig_chg.add_trace(go.Bar(
        x=plot_df['Strike'], y=plot_df['PE_Chg_OI'],
        name='Put Chg in OI', marker_color='#4ade80'
    ))
    fig_chg.add_vline(x=live_spot, line_dash="dash", line_color="#fbbf24")
    fig_chg.update_layout(
        barmode='relative', template='plotly_dark',
        xaxis_title="Strike Price", yaxis_title="Change in OI",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400
    )
    st.plotly_chart(fig_chg, use_container_width=True)

    st.markdown("---")

    # --- CHART 3: Implied Volatility (IV) Smile / Skew Chart ---
    st.markdown("#### 📉 3. Implied Volatility (IV) Smile & Skew Curve")
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(
        x=plot_df['Strike'], y=plot_df['CE_IV'],
        mode='lines+markers', name='Call IV', line=dict(color='#ef4444', width=2)
    ))
    fig_iv.add_trace(go.Scatter(
        x=plot_df['Strike'], y=plot_df['PE_IV'],
        mode='lines+markers', name='Put IV', line=dict(color='#22c55e', width=2)
    ))
    fig_iv.add_vline(x=live_spot, line_dash="dash", line_color="#fbbf24")
    fig_iv.update_layout(
        template='plotly_dark',
        xaxis_title="Strike Price", yaxis_title="Implied Volatility (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400
    )
    st.plotly_chart(fig_iv, use_container_width=True)
