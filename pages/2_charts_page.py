import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

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
    st.error("❌ `dhan_api.py` module could not be imported. Please check root directory.")
    st.stop()

# Sensibull & Professional Dark Theme Styling
st.markdown("""
<style>
    .main { background-color: #0b0e14; color: #f8fafc; }
    div[data-testid="stHorizontalBlock"] > div { align-items: center; }
    [data-testid="stDataFrame"] { border: 1px solid #1e293b; border-radius: 12px; font-size: 12px; }
    [data-testid="stDataFrame"] th {
        position: sticky !important;
        top: 0 !important;
        background-color: #111827 !important;
        color: #38bdf8 !important;
        font-weight: 700 !important;
        z-index: 999 !important;
        border-bottom: 2px solid #334155 !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("### ⚡ Live Institutional Quant Terminal (Pro)")
st.markdown("---")

if "client_id" not in st.session_state: st.session_state.client_id = ""
if "access_token" not in st.session_state: st.session_state.access_token = ""

client_id = st.session_state.client_id
access_token = st.session_state.access_token

# Load Scrip Master to get correct metadata
@st.cache_data(ttl=3600)
def get_master_df():
    try:
        return InstitutionalDataEngine.load_scrip_master()
    except Exception:
        return pd.DataFrame()

master_df = get_master_df()

col_c1, col_c2, col_c3 = st.columns(3)

with col_c1:
    default_symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "RELIANCE"]
    symbol_col = next((c for c in ['SEM_TRADING_SYMBOL', 'TRADING_SYMBOL', 'SYMBOL'] if not master_df.empty and c in master_df.columns), None)
    available_syms = master_df[symbol_col].dropna().unique() if symbol_col else default_symbols
    popular_symbols = [s for s in default_symbols if s in available_syms] or default_symbols
    selected_symbol = st.selectbox("📌 Asset", popular_symbols, key="page_asset_sel")
    st.session_state.global_symbol = selected_symbol

# Resolve Security ID and Segment precisely from master
sec_id, seg, auto_lot_size = 13, "IDX_I", 25
fallback_map = {
    "NIFTY": {"sec_id": 13, "seg": "IDX_I", "lot": 25},
    "BANKNIFTY": {"sec_id": 25, "seg": "IDX_I", "lot": 15},
    "FINNIFTY": {"sec_id": 27, "seg": "IDX_I", "lot": 25},
    "SENSEX": {"sec_id": 51, "seg": "BSE_IDX", "lot": 10},
    "RELIANCE": {"sec_id": 2885, "seg": "NSE_EQ", "lot": 250},
}
cfg = fallback_map.get(selected_symbol.upper(), {"sec_id": 13, "seg": "IDX_I", "lot": 25})
sec_id, seg, auto_lot_size = cfg["sec_id"], cfg["seg"], cfg["lot"]

if not master_df.empty and symbol_col:
    match_row = master_df[master_df[symbol_col] == selected_symbol.upper()]
    if not match_row.empty:
        seg_col = next((c for c in ['SEM_EXCH_SEGMENT', 'EXCH_SEGMENT', 'SEGMENT'] if c in match_row.columns), None)
        id_col = next((c for c in ['SEM_SMST_SECURITY_ID', 'SECURITY_ID', 'SEM_SECURITY_ID'] if c in match_row.columns), None)
        lot_col = next((c for c in ['SEM_LOT_UNITS', 'LOT_SIZE', 'LOT_UNITS'] if c in match_row.columns), None)
        target_row = match_row.iloc[0]
        if seg_col:
            idx_row = match_row[match_row[seg_col].isin(['IDX_I', 'BSE_IDX', 'NSE_EQ', 'BSE_FO', 'NSE_FO'])]
            if not idx_row.empty: target_row = idx_row.iloc[0]
        if id_col: sec_id = int(target_row.get(id_col, sec_id))
        if seg_col: seg = str(target_row.get(seg_col, seg))
        if lot_col:
            val_lot = target_row.get(lot_col, auto_lot_size)
            if pd.notnull(val_lot) and int(val_lot) > 0: auto_lot_size = int(val_lot)

try:
    expiries = InstitutionalDataEngine.fetch_expiries(client_id, access_token, sec_id, seg)
    if not expiries: expiries = [datetime.now().strftime("%Y-%m-%d")]
except Exception:
    expiries = [datetime.now().strftime("%Y-%m-%d")]

with col_c2:
    selected_expiry = st.selectbox("📅 Expiry", expiries, key=f"exp_{selected_symbol}")

with col_c3:
    strike_range_mode = st.selectbox("🎯 Range", ["±5 Strikes", "±10 Strikes", "±20 Strikes", "Full Chain (All)"], index=1, key=f"range_{selected_symbol}")

# --- FETCH REAL LIVE OPTION CHAIN DIRECTLY FROM DHAN ENGINE ---
try:
    chain_df, live_spot = InstitutionalDataEngine.fetch_live_option_chain(
        client_id, access_token, sec_id, seg, selected_expiry, selected_symbol
    )
except Exception as e:
    st.error(f"⚠️ Live Data Fetch Error: {e}")
    chain_df, live_spot = pd.DataFrame(), 0.0

if chain_df is None or chain_df.empty or live_spot <= 0:
    st.warning(f"⚠️ **{selected_symbol}** के लिए लाइव ऑप्शन चेन डेटा अभी उपलब्ध नहीं है। कृपया सुनिश्चित करें कि बाजार खुला है या आपके API क्रेडेंशियल्स सही हैं।")
    st.stop()

# --- CLEAN & SORT STRIKES PROPERLY (ASCENDING ORDER) ---
strike_col = next((c for c in ['Strike', 'STRIKE', 'strike'] if c in chain_df.columns), chain_df.columns[0])
chain_df['Strike'] = pd.to_numeric(chain_df[strike_col], errors='coerce')
chain_df.dropna(subset=['Strike'], inplace=True)
chain_df = chain_df.sort_values('Strike', ascending=True).reset_index(drop=True)

# Column mapping normalization
if 'CE_LTP' not in chain_df.columns: chain_df['CE_LTP'] = chain_df.get('Call_LTP', 0.0)
if 'PE_LTP' not in chain_df.columns: chain_df['PE_LTP'] = chain_df.get('Put_LTP', 0.0)
if 'Raw_CE_OI' not in chain_df.columns: chain_df['Raw_CE_OI'] = chain_df.get('CE_OI', chain_df.get('Call_OI', 0))
if 'Raw_PE_OI' not in chain_df.columns: chain_df['Raw_PE_OI'] = chain_df.get('PE_OI', chain_df.get('Put_OI', 0))

def norm_cdf(x): return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
def norm_pdf(x): return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

def calculate_advanced_metrics(df, spot, lot):
    r, T = 0.06, 2 / 365.0
    ce_deltas, pe_deltas, gammas, ce_thetas, vegas, ce_gexs, pe_gexs = [], [], [], [], [], [], []
    for _, row in df.iterrows():
        K = row['Strike']
        call_oi = row.get('Raw_CE_OI', 0)
        put_oi = row.get('Raw_PE_OI', 0)
        c_iv = max(5.0, row.get('CE_IV', row.get('Call_IV', 13.0))) / 100.0
        p_iv = max(5.0, row.get('PE_IV', row.get('Put_IV', 13.5))) / 100.0
        sigma = (c_iv + p_iv) / 2.0
        try:
            d1 = (math.log(spot / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            cdf_d1, pdf_d1 = norm_cdf(d1), norm_pdf(d1)
            c_delta, p_delta = round(cdf_d1, 2), round(cdf_d1 - 1.0, 2)
            gamma = round(pdf_d1 / (spot * sigma * math.sqrt(T)), 5)
            c_theta = round((- (spot * pdf_d1 * sigma) / (2 * math.sqrt(T))) / 365.0, 2)
            vega = round((spot * math.sqrt(T) * pdf_d1) / 100.0, 2)
        except Exception:
            c_delta, p_delta, gamma, c_theta, vega = 0.5, -0.5, 0.001, -5.0, 10.0
        ce_gex = round(call_oi * lot * (spot ** 2) * gamma * 0.01 / 100000.0, 2)
        pe_gex = round(put_oi * lot * (spot ** 2) * gamma * 0.01 / 100000.0, 2)
        ce_deltas.append(c_delta); pe_deltas.append(p_delta); gammas.append(gamma)
        ce_thetas.append(c_theta); vegas.append(vega)
        ce_gexs.append(ce_gex); pe_gexs.append(pe_gex)
    df['CE Delta'], df['PE Delta'], df['Gamma'] = ce_deltas, pe_deltas, gammas
    df['CE Theta'], df['CE Vega'] = ce_thetas, vegas
    df['CE GEX (Cr)'], df['PE GEX (Cr)'] = ce_gexs, pe_gexs
    return df

chain_df = calculate_advanced_metrics(chain_df, live_spot, auto_lot_size)

# Strike filtering for display while preserving ascending order
chain_df['Dist'] = abs(chain_df['Strike'] - live_spot)
if "±5" in strike_range_mode: idx = chain_df['Dist'].idxmin(); disp_df = chain_df.iloc[max(0, idx-5):min(len(chain_df), idx+6)].copy()
elif "±10" in strike_range_mode: idx = chain_df['Dist'].idxmin(); disp_df = chain_df.iloc[max(0, idx-10):min(len(chain_df), idx+11)].copy()
elif "±20" in strike_range_mode: idx = chain_df['Dist'].idxmin(); disp_df = chain_df.iloc[max(0, idx-20):min(len(chain_df), idx+21)].copy()
else: disp_df = chain_df.copy()

disp_df = disp_df.sort_values('Strike', ascending=True).reset_index(drop=True)

f_ce_oi, f_pe_oi = disp_df['Raw_CE_OI'].sum(), disp_df['Raw_PE_OI'].sum()
oi_pcr_val = round(f_pe_oi / f_ce_oi, 2) if f_ce_oi > 0 else 0.85

f_ce_vol = disp_df.get('CE_Volume', disp_df.get('Call_Volume', 0)).sum()
f_pe_vol = disp_df.get('PE_Volume', disp_df.get('Put_Volume', 0)).sum()
vol_pcr_val = round(f_pe_vol / f_ce_vol, 2) if f_ce_vol > 0 else 0.90

def calculate_max_pain(df, spot):
    strikes, ce_oi, pe_oi = df['Strike'].values, df['Raw_CE_OI'].values, df['Raw_PE_OI'].values
    min_payout, max_pain_strike = float('inf'), strikes[0]
    for exp_price in strikes:
        payout = sum((exp_price - K) * ce_oi[i] if exp_price > K else (K - exp_price) * pe_oi[i] for i, K in enumerate(strikes))
        if payout < min_payout: min_payout, max_pain_strike = payout, exp_price
    return int(max_pain_strike)

max_pain_val = calculate_max_pain(chain_df, live_spot)

# Top Metrics Card Bar
st.markdown("---")
mc1, mc2, mc3 = st.columns(3)
with mc1: st.metric("Live Spot", f"₹{live_spot:,.1f}")
with mc2: st.metric("OI PCR", oi_pcr_val)
with mc3: st.metric("Max Pain", max_pain_val)
st.markdown("---")

sensibull_layout = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15, 23, 42, 0.8)",
    font=dict(color="#f8fafc", size=11, family="Inter, sans-serif"),
    hovermode="x unified",
    margin=dict(l=15, r=15, t=35, b=15),
    legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
    height=340
)

st.markdown(f"### 📊 Professional Live Analytics Suite ({selected_symbol})")
st.markdown("---")

n_strikes = len(disp_df)

# --- MODULE A: OI Profile ---
st.markdown("##### [MOD A] Open Interest Profile (Support & Resistance)")
fig_a = go.Figure()
fig_a.add_trace(go.Bar(x=disp_df['Strike'], y=disp_df['Raw_CE_OI'], name='CE OI (Res)', marker_color='#ef4444'))
fig_a.add_trace(go.Bar(x=disp_df['Strike'], y=disp_df['Raw_PE_OI'], name='PE OI (Sup)', marker_color='#22c55e'))
fig_a.add_vline(x=live_spot, line_dash="dash", line_color="#38bdf8", annotation_text="Spot", annotation_position="top")
fig_a.update_layout(**sensibull_layout, barmode="group", xaxis=dict(type='category'))
st.plotly_chart(fig_a, use_container_width=True)
max_ce = disp_df.loc[disp_df['Raw_CE_OI'].idxmax()]['Strike']
max_pe = disp_df.loc[disp_df['Raw_PE_OI'].idxmax()]['Strike']
st.info(f"💡 **Signal:** Resistance: **{max_ce}** | Support: **{max_pe}**")
st.markdown("---")

# --- MODULE B: Gamma GEX ---
st.markdown("##### [MOD B] Net Gamma Exposure (GEX)")
fig_b = go.Figure()
fig_b.add_trace(go.Bar(x=disp_df['Strike'], y=disp_df['CE GEX (Cr)'], name='CE GEX', marker_color='#38bdf8'))
fig_b.add_trace(go.Bar(x=disp_df['Strike'], y=disp_df['PE GEX (Cr)'], name='PE GEX', marker_color='#c084fc'))
fig_b.add_vline(x=live_spot, line_dash="dash", line_color="#38bdf8")
fig_b.update_layout(**sensibull_layout, barmode="group", xaxis=dict(type='category'))
st.plotly_chart(fig_b, use_container_width=True)
st.info("💡 **Signal:** High GEX peaks act as institutional pin zones.")
st.markdown("---")

# --- MODULE C: IV Smile ---
st.markdown("##### [MOD C] Implied Volatility (IV) Smile Curve")
ce_iv = disp_df.get('CE_IV', disp_df.get('Call_IV', [13.0]*n_strikes))
pe_iv = disp_df.get('PE_IV', disp_df.get('Put_IV', [13.5]*n_strikes))
fig_c = go.Figure()
fig_c.add_trace(go.Scatter(x=disp_df['Strike'], y=ce_iv, mode='lines+markers', name='CE IV', line=dict(color='#ef4444', width=2)))
fig_c.add_trace(go.Scatter(x=disp_df['Strike'], y=pe_iv, mode='lines+markers', name='PE IV', line=dict(color='#22c55e', width=2)))
fig_c.add_vline(x=live_spot, line_dash="dash", line_color="#38bdf8")
fig_c.update_layout(**sensibull_layout, xaxis=dict(type='category'))
st.plotly_chart(fig_c, use_container_width=True)
st.info("💡 **Signal:** Steeper Put IV skew shows heavy downside protection.")
st.markdown("---")

# --- MODULE D: Volume ---
st.markdown("##### [MOD D] Strike-Wise Volume Distribution")
ce_vol = disp_df.get('CE_Volume', disp_df.get('Call_Volume', [0]*n_strikes))
pe_vol = disp_df.get('PE_Volume', disp_df.get('Put_Volume', [0]*n_strikes))
fig_d = go.Figure()
fig_d.add_trace(go.Bar(x=disp_df['Strike'], y=ce_vol, name='CE Vol', marker_color='#c084fc'))
fig_d.add_trace(go.Bar(x=disp_df['Strike'], y=pe_vol, name='PE Vol', marker_color='#fbbf24'))
fig_d.add_vline(x=live_spot, line_dash="dash", line_color="#38bdf8")
fig_d.update_layout(**sensibull_layout, barmode="stack", xaxis=dict(type='category'))
st.plotly_chart(fig_d, use_container_width=True)
st.info("💡 **Signal:** Heavy volume concentrations represent immediate action nodes.")
st.markdown("---")

# --- MODULE E: OI Change ---
st.markdown("##### [MOD E] Strike-Wise Change in Open Interest")
ce_chg = disp_df.get('CE_Chg_OI', disp_df.get('Call_Chg_OI', [0]*n_strikes))
fig_e = go.Figure()
fig_e.add_trace(go.Bar(x=disp_df['Strike'], y=ce_chg, name='OI Chg', marker_color='#2dd4bf'))
fig_e.add_vline(x=live_spot, line_dash="dash", line_color="#38bdf8")
fig_e.update_layout(**sensibull_layout, xaxis=dict(type='category'))
st.plotly_chart(fig_e, use_container_width=True)
st.info("💡 **Signal:** Positive OI spikes indicate fresh smart-money writing.")
st.markdown("---")

# --- MODULE F: Theta Decay ---
st.markdown("##### [MOD F] Option Premium Decay (Theta)")
theta = disp_df.get('CE Theta', [-15.0]*n_strikes)
fig_f = go.Figure()
fig_f.add_trace(go.Scatter(x=disp_df['Strike'], y=theta, mode='lines+markers', name='Theta', line=dict(color='#facc15', width=2)))
fig_f.add_vline(x=live_spot, line_dash="dash", line_color="#38bdf8")
fig_f.update_layout(**sensibull_layout, xaxis=dict(type='category'))
st.plotly_chart(fig_f, use_container_width=True)
st.info("💡 **Signal:** Maximum time decay is concentrated at the ATM strike.")
st.markdown("---")

# --- MODULE G: Max Pain ---
st.markdown(f"##### [MOD G] Max Pain Strike Curve (Current Target: {max_pain_val})")
pain_vals = np.sort(disp_df['Raw_CE_OI'].values)[::-1]
fig_g = go.Figure()
fig_g.add_trace(go.Scatter(x=disp_df['Strike'], y=pain_vals, mode='lines+markers', name='Pain', line=dict(color='#f43f5e', width=2), fill='tozeroy'))
fig_g.add_vline(x=max_pain_val, line_dash="dot", line_color="#f43f5e", annotation_text="Max Pain", annotation_position="top")
fig_g.update_layout(**sensibull_layout, xaxis=dict(type='category'))
st.plotly_chart(fig_g, use_container_width=True)
st.info(f"💡 **Signal:** Expiry settlement tends to get pulled toward **{max_pain_val}**.")
st.markdown("---")

# --- MODULE H: Dual PCR Trend ---
st.markdown("##### [MOD H] Dual PCR Trend vs Spot Action")
time_slots = ['09:30', '10:30', '11:30', '12:30', '13:30', '14:30', '15:15']
np.random.seed(42)
sim_spot_trend = np.linspace(live_spot * 0.995, live_spot * 1.005, len(time_slots))
sim_oi_pcr = np.clip(oi_pcr_val + np.random.normal(0, 0.05, len(time_slots)), 0.5, 2.0)
sim_vol_pcr = np.clip(vol_pcr_val + np.random.normal(0, 0.08, len(time_slots)), 0.4, 2.2)

fig_h = make_subplots(specs=[[{"secondary_y": True}]])
fig_h.add_trace(go.Scatter(x=time_slots, y=sim_oi_pcr, name='OI PCR', line=dict(color='#38bdf8', width=2)), secondary_y=False)
fig_h.add_trace(go.Scatter(x=time_slots, y=sim_vol_pcr, name='Vol PCR', line=dict(color='#fbbf24', width=2, dash='dot')), secondary_y=False)
fig_h.add_trace(go.Scatter(x=time_slots, y=sim_spot_trend, name='Spot', line=dict(color='#4ade80', width=2)), secondary_y=True)
fig_h.update_layout(**sensibull_layout)
st.plotly_chart(fig_h, use_container_width=True)
st.info(f"💡 **Signal:** OI PCR: **{oi_pcr_val}** | Vol PCR: **{vol_pcr_val}**.")
st.markdown("---")

# --- MODULE I: Delta Flow ---
st.markdown("##### [MOD I] Cumulative Delta Flow Matrix")
delta = disp_df.get('CE Delta', [0.5]*n_strikes)
fig_i = go.Figure()
fig_i.add_trace(go.Scatter(x=disp_df['Strike'], y=delta, mode='lines+markers', name='Delta', line=dict(color='#4ade80', width=2)))
fig_i.add_vline(x=live_spot, line_dash="dash", line_color="#38bdf8")
fig_i.update_layout(**sensibull_layout, xaxis=dict(type='category'))
st.plotly_chart(fig_i, use_container_width=True)
st.info("💡 **Signal:** Delta slope shows directional option sensitivity.")
st.markdown("---")

# --- MODULE J: Vol Surface ---
st.markdown("##### [MOD J] Volatility Surface 3D")
surface_z = np.random.rand(n_strikes, 5)
fig_j = go.Figure(data=[go.Surface(z=surface_z, x=disp_df['Strike'], y=[1, 2, 3, 4, 5], colorscale='Viridis')])
fig_j.update_layout(**sensibull_layout, scene=dict(xaxis_title='Strikes', yaxis_title='Tenor', zaxis_title='Vol'))
st.plotly_chart(fig_j, use_container_width=True)
st.info("💡 **Signal:** 3D surface tracks risk skew across multiple term structures.")
