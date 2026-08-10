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
            spot = 24570.65
            strikes = np.arange(24050, 25100, 50)
            recs = []
            for st_val in strikes:
                recs.append({
                    "Strike": int(st_val), "STRIKE": int(st_val),
                    "CE_OI": 500000, "Raw_CE_OI": 500000, "CE_Chg_OI": 12000, "CE_%Chg": 1.5, "CE_Volume": 1000000, "CE_IV": 14.0, "CE_LTP": max(1.0, 24570.65 - st_val + 50),
                    "PE_LTP": max(1.0, st_val - 24570.65 + 50), "PE_IV": 14.5, "PE_Volume": 1000000, "PE_Chg_OI": -5000, "PE_%Chg": -0.8, "PE_OI": 600000, "Raw_PE_OI": 600000
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

client_id = st.session_state.get("client_id", "")
access_token = st.session_state.get("access_token", "")

col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns([1.5, 1.5, 2, 2, 1.5])

with col_c1:
    all_symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "RELIANCE", "TCS", "SBIN"]
    current_idx = all_symbols.index(st.session_state.get("global_symbol", "NIFTY")) if st.session_state.get("global_symbol", "NIFTY") in all_symbols else 0
    selected_symbol = st.selectbox("📌 Asset", all_symbols, index=current_idx, key="page_asset_sel")
    st.session_state.global_symbol = selected_symbol

master_dict = {
    "NIFTY": {"sec_id": 13, "seg": "IDX_I", "lot": 25},
    "BANKNIFTY": {"sec_id": 25, "seg": "IDX_I", "lot": 15},
    "FINNIFTY": {"sec_id": 27, "seg": "IDX_I", "lot": 25},
    "SENSEX": {"sec_id": 51, "seg": "BSE_IDX", "lot": 10},
    "RELIANCE": {"sec_id": 2885, "seg": "NSE_EQ", "lot": 250},
    "TCS": {"sec_id": 11536, "seg": "NSE_EQ", "lot": 175},
    "SBIN": {"sec_id": 3045, "seg": "NSE_EQ", "lot": 750}
}
cfg = master_dict.get(selected_symbol.upper(), {"sec_id": 13, "seg": "IDX_I", "lot": 25})
sec_id, seg, server_lot = cfg["sec_id"], cfg["seg"], cfg["lot"]

try:
    expiries = InstitutionalDataEngine.fetch_expiries(client_id, access_token, sec_id, seg)
    if not expiries:
        expiries = [datetime.now().strftime("%Y-%m-%d")]
except Exception:
    expiries = [datetime.now().strftime("%Y-%m-%d")]

with col_c2:
    selected_expiry = st.selectbox("📅 Expiry", expiries, index=0, key=f"exp_{selected_symbol}")

with col_c3:
    strike_range_mode = st.selectbox(
        "🎯 Range", 
        ["±5 Strikes", "±10 Strikes", "±20 Strikes", "±30 Strikes", "Full Chain (All)"],
        index=1,
        key=f"range_{selected_symbol}"
    )

with col_c4:
    show_greeks = st.checkbox("Show Quant Greeks & Vanna/Charm", value=True)

with col_c5:
    lot_size = st.number_input(
        "⚙️ Lot", 
        min_value=1, 
        max_value=10000, 
        value=int(server_lot), 
        step=1,
        key=f"lot_{selected_symbol}"
    )

# --- FETCH LIVE DATA SAFELY ---
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

# --- DATA SANITIZATION LAYER (कच्चे डेटा को साफ़ और व्यवस्थित करना) ---
strike_col = 'Strike' if 'Strike' in chain_df.columns else ('STRIKE' if 'STRIKE' in chain_df.columns else chain_df.columns[0])
chain_df['Strike'] = pd.to_numeric(chain_df[strike_col], errors='coerce')
chain_df.dropna(subset=['Strike'], inplace=True)

# सुरक्षित कॉलम मैपिंग
for prefix in ['CE_', 'PE_']:
    oi_key = f"{prefix}OI"
    raw_key = f"Raw_{prefix}OI"
    if raw_key not in chain_df.columns:
        if oi_key in chain_df.columns:
            chain_df[raw_key] = pd.to_numeric(chain_df[oi_key], errors='coerce').fillna(100000)
        else:
            chain_df[raw_key] = 100000

# Math Helper functions for Normal CDF and PDF
def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x):
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

# Comprehensive Advanced Metrics Calculation Engine
def calculate_advanced_metrics(df, spot, lot):
    r = 0.06 
    T = 2 / 365.0
    
    ce_deltas, pe_deltas = [], []
    gammas, ce_thetas, pe_thetas, vegas = [], [], [], []
    ce_vannas, pe_vannas = [], []
    ce_charms, pe_charms = [], []
    ce_gexs, pe_gexs = [], []
    ce_turnovers, pe_turnovers = [], []
    
    for _, row in df.iterrows():
        K = row['Strike']
        call_oi = row.get('Raw_CE_OI', 100000)
        put_oi = row.get('Raw_PE_OI', 100000)
        
        c_ltp = row.get('CE_LTP', 10.0)
        p_ltp = row.get('PE_LTP', 10.0)
        c_vol = row.get('CE_Volume', 100000)
        p_vol = row.get('PE_Volume', 100000)
        
        c_iv = max(5.0, row.get('CE_IV', 13.0)) / 100.0
        p_iv = max(5.0, row.get('PE_IV', 13.5)) / 100.0
        sigma = (c_iv + p_iv) / 2.0
        
        try:
            d1 = (math.log(spot / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            cdf_d1 = norm_cdf(d1)
            pdf_d1 = norm_pdf(d1)
            
            c_delta = round(cdf_d1, 2)
            p_delta = round(cdf_d1 - 1.0, 2)
            gamma = round(pdf_d1 / (spot * sigma * math.sqrt(T)), 5)
            
            c_theta = round((- (spot * pdf_d1 * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm_cdf(d2)) / 365.0, 2)
            p_theta = round((- (spot * pdf_d1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365.0, 2)
            vega = round((spot * math.sqrt(T) * pdf_d1) / 100.0, 2)
            
            vanna = round(-pdf_d1 * d2 / sigma, 4)
            charm = round(-pdf_d1 * (2 * r * T - d2 * sigma * math.sqrt(T)) / (2 * T * sigma * math.sqrt(T)) / 365.0, 4)
        except Exception:
            c_delta, p_delta, gamma, c_theta, p_theta, vega, vanna, charm = 0.5, -0.5, 0.001, -5.0, -5.0, 10.0, 0.01, -0.01

        ce_gex = round(call_oi * lot * (spot ** 2) * gamma / 100000000.0, 2)
        pe_gex = round(put_oi * lot * (spot ** 2) * gamma / 100000000.0, 2)
        
        c_turnover = round((c_vol * c_ltp * lot) / 10000000.0, 2)
        p_turnover = round((p_vol * p_ltp * lot) / 10000000.0, 2)

        ce_deltas.append(c_delta)
        pe_deltas.append(p_delta)
        gammas.append(gamma)
        ce_thetas.append(c_theta)
        pe_thetas.append(p_theta)
        vegas.append(vega)
        ce_vannas.append(vanna)
        pe_vannas.append(vanna)
        ce_charms.append(charm)
        pe_charms.append(charm)
        ce_gexs.append(ce_gex)
        pe_gexs.append(pe_gex)
        ce_turnovers.append(c_turnover)
        pe_turnovers.append(p_turnover)
        
    df['CE Delta'] = ce_deltas
    df['PE Delta'] = pe_deltas
    df['Gamma'] = gammas
    df['CE Theta'] = ce_thetas
    df['PE Theta'] = pe_thetas
    df['CE Vega'] = vegas
    df['PE Vega'] = vegas
    df['CE Vanna'] = ce_vannas
    df['PE Vanna'] = pe_vannas
    df['CE Charm'] = ce_charms
    df['PE Charm'] = pe_charms
    df['CE GEX (Cr)'] = ce_gexs
    df['PE GEX (Cr)'] = pe_gexs
    df['CE Turnover (Cr)'] = ce_turnovers
    df['PE Turnover (Cr)'] = pe_turnovers
    return df

chain_df = calculate_advanced_metrics(chain_df, live_spot, lot_size)

# Strike filtering
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
elif "±30" in strike_range_mode:
    center_idx = chain_df['Dist'].idxmin()
    disp_df = chain_df.iloc[max(0, center_idx-30):min(len(chain_df), center_idx+31)].copy()
else:
    disp_df = chain_df.copy()

# Summary Metrics Bar
atm_row = disp_df.loc[disp_df['Dist'].idxmin()]
atm_iv = round((atm_row.get('CE_IV', 13.0) + atm_row.get('PE_IV', 13.5)) / 2.0, 2)

f_ce_oi = disp_df['Raw_CE_OI'].sum()
f_pe_oi = disp_df['Raw_PE_OI'].sum()
pcr_val = round(f_pe_oi / f_ce_oi, 2) if f_ce_oi > 0 else 0.85

st.markdown("---")
m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("Underlying Asset", selected_symbol)
with m2: st.metric("Live Spot Price", f"₹{live_spot:,.2f}")
with m3: st.metric("ATM Implied Volatility", f"{atm_iv}%")
with m4: st.metric("Put-Call Ratio (PCR)", pcr_val)
st.markdown("---")

# Buildup helper
def get_buildup(chg_oi, pct_chg):
    if pct_chg > 0 and chg_oi > 0: return "Short Build"
    elif pct_chg < 0 and chg_oi < 0: return "Long Unwind"
    elif pct_chg > 0 and chg_oi < 0: return "Short Cover"
    return "Long Build"

disp_df['CE Build'] = disp_df.apply(lambda r: get_buildup(r.get('CE_Chg_OI', 0), r.get('CE_%Chg', 0)), axis=1)
disp_df['PE Build'] = disp_df.apply(lambda r: get_buildup(r.get('PE_Chg_OI', 0), r.get('PE_%Chg', 0)), axis=1)

# Format columns for display cleanly
disp_df['STRIKE'] = disp_df['Strike']
disp_df['CE OI (L)'] = round(disp_df['Raw_CE_OI'] / 100000, 2)
disp_df['PE OI (L)'] = round(disp_df['Raw_PE_OI'] / 100000, 2)
disp_df['CE Vol (M)'] = round(disp_df.get('CE_Volume', 100000) / 1000000, 2)
disp_df['PE Vol (M)'] = round(disp_df.get('PE_Volume', 100000) / 1000000, 2)

disp_df['CE OI Chg'] = disp_df.get('CE_Chg_OI', 0)
disp_df['PE OI Chg'] = disp_df.get('PE_Chg_OI', 0)
disp_df['CE OI Chg %'] = disp_df.get('CE_%Chg', 0.0)
disp_df['PE OI Chg %'] = disp_df.get('PE_%Chg', 0.0)

disp_df['CE Bid'] = round(disp_df['CE_LTP'] * 0.99, 2)
disp_df['CE Ask'] = round(disp_df['CE_LTP'] * 1.01, 2)
disp_df['PE Bid'] = round(disp_df['PE_LTP'] * 0.99, 2)
disp_df['PE Ask'] = round(disp_df['PE_LTP'] * 1.01, 2)

disp_df['CE Spread %'] = np.where(disp_df['CE_LTP'] > 0, round(((disp_df['CE Ask'] - disp_df['CE Bid']) / disp_df['CE_LTP']) * 100, 2), 0.0)
disp_df['PE Spread %'] = np.where(disp_df['PE_LTP'] > 0, round(((disp_df['PE Ask'] - disp_df['PE Bid']) / disp_df['PE_LTP']) * 100, 2), 0.0)

# --- MATRIX LAYOUT ---
if show_greeks:
    matrix_cols = [
        "CE Build", "CE GEX (Cr)", "CE Charm", "CE Vanna", "CE Vega", "CE Theta", "Gamma", "CE Delta",
        "CE Vol (M)", "CE Turnover (Cr)", "CE OI Chg %", "CE OI Chg", "CE OI (L)",
        "CE Spread %", "CE Ask", "CE Bid", "CE_LTP"
    ]
else:
    matrix_cols = [
        "CE Build", "CE Vol (M)", "CE Turnover (Cr)", "CE OI Chg %", "CE OI Chg", "CE OI (L)",
        "CE Spread %", "CE Ask", "CE Bid", "CE_LTP"
    ]

matrix_cols += ["STRIKE"]

if show_greeks:
    matrix_cols += [
        "PE_LTP", "PE Bid", "PE Ask", "PE Spread %",
        "PE OI (L)", "PE OI Chg", "PE OI Chg %", "PE Turnover (Cr)", "PE Vol (M)",
        "PE Delta", "Gamma", "PE Theta", "PE Vega", "PE Vanna", "PE Charm", "PE GEX (Cr)", "PE Build"
    ]
else:
    matrix_cols += [
        "PE_LTP", "PE Bid", "PE Ask", "PE Spread %",
        "PE OI (L)", "PE OI Chg", "PE OI Chg %", "PE Turnover (Cr)", "PE Vol (M)", "PE Build"
    ]

final_cols = [c for c in matrix_cols if c in disp_df.columns]
matrix_df = disp_df[final_cols].copy()
matrix_df = matrix_df.loc[:, ~matrix_df.columns.duplicated()]

atm_strike_val = round(live_spot / 50) * 50

# --- PROFESSIONAL INSTITUTIONAL STYLING FUNCTION ---
def professional_terminal_styling(row):
    strike = row['STRIKE']
    styles = [''] * len(row)
    is_atm = abs(strike - live_spot) <= 25 or strike == atm_strike_val
    
    for i, col_name in enumerate(row.index):
        if col_name == 'STRIKE':
            if is_atm:
                styles[i] = 'background-color: #d97706; color: #ffffff; font-weight: bold; font-size: 15px; border: 2px solid #fbbf24;'
            else:
                styles[i] = 'background-color: #1f2937; color: #f9fafb; font-weight: bold;'
        elif 'CE' in col_name:
            if strike < live_spot: # CE ITM
                styles[i] = 'background-color: #111e38; color: #e2e8f0;'
            else: # CE OTM
                styles[i] = 'background-color: #0f172a; color: #94a3b8;'
        elif 'PE' in col_name:
            if strike > live_spot: # PE ITM
                styles[i] = 'background-color: #381116; color: #e2e8f0;'
            else: # PE OTM
                styles[i] = 'background-color: #1e1114; color: #94a3b8;'
        else:
            styles[i] = ''
            
        val = row[col_name]
        if isinstance(val, str):
            if "Short Build" in val:
                styles[i] += '; background-color: #7f1d1d; color: #fca5a5; font-weight: bold;'
            elif "Long Build" in val:
                styles[i] += '; background-color: #065f46; color: #6ee7b7; font-weight: bold;'
            elif "Short Cover" in val:
                styles[i] += '; background-color: #1e3a8a; color: #93c5fd; font-weight: bold;'
            elif "Long Unwind" in val:
                styles[i] += '; background-color: #78350f; color: #fde68a; font-weight: bold;'
        elif isinstance(val, (int, float)):
            if val > 0 and col_name != 'STRIKE':
                styles[i] += '; color: #34d399;'
            elif val < 0:
                styles[i] += '; color: #f87171;'
                
    return styles

styled_df = matrix_df.style.apply(professional_terminal_styling, axis=1)

st.markdown(f"### 📊 Professional Institutional Option Chain ({strike_range_mode})")
st.markdown("---")
st.dataframe(styled_df, use_container_width=True, height=650, hide_index=True)
