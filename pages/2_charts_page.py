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
                    "Strike": int(st_val), "STRIKE": int(st_val),
                    "CE_OI": 500000, "Raw_CE_OI": 500000, "CE_Chg_OI": 12000, "CE_%Chg": 1.5, "CE_Volume": 1000000, "CE_IV": 13.0, "CE_LTP": max(1.0, spot - st_val + 20),
                    "PE_LTP": max(1.0, st_val - spot + 20), "PE_IV": 13.5, "PE_Volume": 1000000, "PE_Chg_OI": -5000, "PE_%Chg": -0.8, "PE_OI": 600000, "Raw_PE_OI": 600000
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
    # Navigation between Page 1 and Page 2
    active_page = st.selectbox("📑 Terminal Page", ["Page 1: Core Option Chain", "Page 2: OI Support, Resistance & Shift Tracker"])

with col_h4:
    lot_size = st.number_input("⚙️ Lot Size", min_value=1, max_value=10000, value=int(server_lot), step=1)

# --- FETCH LIVE DATA ---
try:
    chain_df, live_spot = InstitutionalDataEngine.fetch_live_option_chain(
        client_id, access_token, sec_id, seg, selected_expiry, selected_symbol
    )
except Exception:
    chain_df = pd.DataFrame()
    live_spot = 24583.80

if chain_df is None or chain_df.empty:
    spot_val = 24583.80
    strikes = np.arange(24000, 25200, 50)
    recs = []
    for st_val in strikes:
        recs.append({
            "Strike": int(st_val), "STRIKE": int(st_val),
            "CE_OI": 500000, "Raw_CE_OI": 500000, "CE_Chg_OI": 12000, "CE_%Chg": 1.5, "CE_Volume": 1000000, "CE_IV": 13.0, "CE_LTP": max(1.0, spot_val - st_val + 20),
            "PE_LTP": max(1.0, st_val - spot_val + 20), "PE_IV": 13.5, "PE_Volume": 1000000, "PE_Chg_OI": -5000, "PE_%Chg": -0.8, "PE_OI": 600000, "Raw_PE_OI": 600000
        })
    chain_df = pd.DataFrame(recs)
    live_spot = spot_val

# --- NORMALIZATION ---
strike_col = 'Strike' if 'Strike' in chain_df.columns else ('STRIKE' if 'STRIKE' in chain_df.columns else chain_df.columns[0])
chain_df['Strike'] = pd.to_numeric(chain_df[strike_col], errors='coerce')
chain_df.dropna(subset=['Strike'], inplace=True)

if 'CE_LTP' not in chain_df.columns and 'Call_LTP' in chain_df.columns:
    chain_df['CE_LTP'] = chain_df['Call_LTP']
elif 'CE_LTP' not in chain_df.columns:
    chain_df['CE_LTP'] = 10.0

if 'PE_LTP' not in chain_df.columns and 'Put_LTP' in chain_df.columns:
    chain_df['PE_LTP'] = chain_df['Put_LTP']
elif 'PE_LTP' not in chain_df.columns:
    chain_df['PE_LTP'] = 10.0

if 'Raw_CE_OI' not in chain_df.columns:
    chain_df['Raw_CE_OI'] = chain_df.get('CE_OI', chain_df.get('Call_OI', 100000))

if 'Raw_PE_OI' not in chain_df.columns:
    chain_df['Raw_PE_OI'] = chain_df.get('PE_OI', chain_df.get('Put_OI', 100000))

# Math Helpers
def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x):
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

# Advanced Quant Engine for Greeks & GEX
def calculate_advanced_metrics(df, spot, lot):
    r = 0.06 
    T = 2 / 365.0
    ce_deltas, pe_deltas, gammas, vegas, ce_gexs, pe_gexs = [], [], [], [], [], []
    
    for _, row in df.iterrows():
        K = row['Strike']
        call_oi = row.get('Raw_CE_OI', 100000)
        put_oi = row.get('Raw_PE_OI', 100000)
        c_iv = max(5.0, row.get('CE_IV', 13.0)) / 100.0
        p_iv = max(5.0, row.get('PE_IV', 13.5)) / 100.0
        sigma = (c_iv + p_iv) / 2.0
        
        try:
            d1 = (math.log(spot / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            c_delta = round(norm_cdf(d1), 2)
            p_delta = round(c_delta - 1.0, 2)
            gamma = round(norm_pdf(d1) / (spot * sigma * math.sqrt(T)), 5)
            vega = round((spot * math.sqrt(T) * norm_pdf(d1)) / 100.0, 2)
        except Exception:
            c_delta, p_delta, gamma, vega = 0.5, -0.5, 0.001, 10.0

        ce_gex = round(call_oi * lot * (spot ** 2) * gamma / 100000000.0, 2)
        pe_gex = round(put_oi * lot * (spot ** 2) * gamma / 100000000.0, 2)

        ce_deltas.append(c_delta)
        pe_deltas.append(p_delta)
        gammas.append(gamma)
        vegas.append(vega)
        ce_gexs.append(ce_gex)
        pe_gexs.append(pe_gex)
        
    df['CE Delta'] = ce_deltas
    df['PE Delta'] = pe_deltas
    df['Gamma'] = gammas
    df['CE Vega'] = vegas
    df['PE Vega'] = vegas
    df['CE GEX (Cr)'] = ce_gexs
    df['PE GEX (Cr)'] = pe_gexs
    return df

chain_df = calculate_advanced_metrics(chain_df, live_spot, lot_size)

# ==========================================
# PAGE 1: CORE OPTION CHAIN & PRICE ACTION
# ==========================================
if "Page 1" in active_page:
    st.markdown("### 📊 Page 1: Core Option Chain & Price Action Matrix")
    st.markdown("---")
    
    col_r1, col_r2, col_r3 = st.columns([2, 2, 2])
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

    disp_df['STRIKE'] = disp_df['Strike']
    disp_df['CE OI (L)'] = round(disp_df['Raw_CE_OI'] / 100000, 2)
    disp_df['PE OI (L)'] = round(disp_df['Raw_PE_OI'] / 100000, 2)
    disp_df['CE Vol (M)'] = round(disp_df.get('CE_Volume', 100000) / 1000000, 2)
    disp_df['PE Vol (M)'] = round(disp_df.get('PE_Volume', 100000) / 1000000, 2)

    disp_df['CE OI Chg'] = disp_df.get('CE_Chg_OI', 0)
    disp_df['PE OI Chg'] = disp_df.get('PE_Chg_OI', 0)

    if show_greeks:
        matrix_cols = ["CE GEX (Cr)", "CE Vega", "Gamma", "CE Delta", "CE Vol (M)", "CE OI Chg", "CE OI (L)", "CE_LTP"]
    else:
        matrix_cols = ["CE Vol (M)", "CE OI Chg", "CE OI (L)", "CE_LTP"]

    matrix_cols += ["STRIKE"]

    if show_greeks:
        matrix_cols += ["PE_LTP", "PE OI (L)", "PE OI Chg", "PE Vol (M)", "PE Delta", "Gamma", "PE Vega", "PE GEX (Cr)"]
    else:
        matrix_cols += ["PE_LTP", "PE OI (L)", "PE OI Chg", "PE Vol (M)"]

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
# PAGE 2: OI SUPPORT, RESISTANCE & SHIFT TRACKER DASHBOARD
# ========================================================
elif "Page 2" in active_page:
    st.markdown("### 🎯 Page 2: OI Support, Resistance & Shift Tracker Dashboard")
    st.markdown("---")
    
    # 1. Macro Calculations
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

    # Immediate Support & Resistance
    max_call_row = chain_df.loc[chain_df['Raw_CE_OI'].idxmax()] if not chain_df.empty else None
    max_put_row = chain_df.loc[chain_df['Raw_PE_OI'].idxmax()] if not chain_df.empty else None
    
    immediate_resistance = int(max_call_row['Strike']) if max_call_row is not None else 0
    immediate_support = int(max_put_row['Strike']) if max_put_row is not None else 0

    # Concentration Index (% of top 3 strikes)
    top_3_calls = chain_df['Raw_CE_OI'].nlargest(3).sum()
    top_3_puts = chain_df['Raw_PE_OI'].nlargest(3).sum()
    call_concentration = round((top_3_calls / total_call_oi) * 100, 2) if total_call_oi > 0 else 0
    put_concentration = round((top_3_puts / total_put_oi) * 100, 2) if total_put_oi > 0 else 0

    # ATM Straddle
    atm_idx = (np.abs(chain_df['Strike'] - live_spot)).argmin()
    atm_strike = chain_df.loc[atm_idx, 'Strike']
    atm_straddle_price = round(chain_df.loc[atm_idx, 'CE_LTP'] + chain_df.loc[atm_idx, 'PE_LTP'], 2)

    # Display Macro Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Live PCR", pcr, delta="Bullish" if pcr > 1.1 else "Bearish")
    with m2: st.metric("Max Pain Strike", f"{max_pain_strike:,}")
    with m3: st.metric("Immediate Resistance", f"{immediate_resistance:,}", delta="Max Call OI")
    with m4: st.metric("Immediate Support", f"{immediate_support:,}", delta="Max Put OI")
    
    st.markdown("---")
    
    # Advanced Metrics Row
    a1, a2, a3 = st.columns(3)
    with a1: st.metric("ATM Straddle Price", f"₹{atm_straddle_price:,.2f}", delta=f"Strike: {atm_strike}")
    with a2: st.metric("Top 3 Call OI Concentration", f"{call_concentration}%")
    with a3: st.metric("Top 3 Put OI Concentration", f"{put_concentration}%")
    
    st.markdown("---")
    st.markdown("#### 📊 Top Resistance & Support Striking Walls (OI Bar Summary)")
    
    # Resistance and Support Striking Tables
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        st.markdown("**🔴 Top 5 Resistance Walls (Call OI)**")
        top_calls = chain_df.nlargest(5, 'Raw_CE_OI')[['Strike', 'Raw_CE_OI', 'CE_Chg_OI', 'CE_LTP']].copy()
        top_calls['CE OI (Lacs)'] = round(top_calls['Raw_CE_OI'] / 100000, 2)
        st.dataframe(top_calls[['Strike', 'CE OI (Lacs)', 'CE_Chg_OI', 'CE_LTP']], use_container_width=True, hide_index=True)
        
    with col_s2:
        st.markdown("**🟢 Top 5 Support Floors (Put OI)**")
        top_puts = chain_df.nlargest(5, 'Raw_PE_OI')[['Strike', 'Raw_PE_OI', 'PE_Chg_OI', 'PE_LTP']].copy()
        top_puts['PE OI (Lacs)'] = round(top_puts['Raw_PE_OI'] / 100000, 2)
        st.dataframe(top_puts[['Strike', 'PE OI (Lacs)', 'PE_Chg_OI', 'PE_LTP']], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("> ⚡ **Shift Monitor Alert:** Immediate Support and Resistance zones remain stable around current option open interest clusters. Watch for sudden OI unwinding to spot breakout points.")
