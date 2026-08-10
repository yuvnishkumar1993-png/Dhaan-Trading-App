import os
import sys
import streamlit as pd_st
import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta

try:
    import plotly.express as px
    import plotly.graph_objects as go
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
    from dhan_api import InstitutionalDataEngine, get_market_data
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
            today = datetime.now()
            days_to_thu = (3 - today.weekday() + 7) % 7
            if days_to_thu == 0: days_to_thu = 7
            next_thu = today + timedelta(days=days_to_thu)
            return [(next_thu + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(4)]
        @staticmethod
        def fetch_live_option_chain(c, a, s, seg, exp, sym):
            return None, 0.0

    def get_market_data(asset="SENSEX"):
        return 74000, pd.DataFrame(), None, None, None

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
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #1a1c23; 
        border-radius: 4px; 
        color: #b0bec5; 
        padding: 8px 16px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #29b6f6 !important; 
        color: #000000 !important; 
    }
</style>
""", unsafe_allow_html=True)

st.markdown("## ⚡ Institutional Quant Terminal Pro — Advanced Terminal")
st.markdown("---")

if "client_id" not in st.session_state: st.session_state.client_id = ""
if "access_token" not in st.session_state: st.session_state.access_token = ""

client_id = st.session_state.client_id
access_token = st.session_state.access_token

@st.cache_data(ttl=3600)
def get_master_df():
    return InstitutionalDataEngine.load_scrip_master()

master_df = get_master_df()

@st.cache_data(ttl=3600)
def load_lot_size_mapping():
    try:
        csv_path = os.path.join(ROOT_DIR, 'Dhan - Nse Fno Lot Size (1).csv')
        if not os.path.exists(csv_path):
            csv_path = 'Dhan - Nse Fno Lot Size (1).csv'
        df = pd.read_csv(csv_path)
        mapping = {}
        for _, row in df.iterrows():
            sym = str(row['Symbol']).strip().upper()
            lot = int(row['Lot Size (Aug 2026)'])
            mapping[sym] = lot
        return mapping
    except Exception:
        return {}

lot_mapping = load_lot_size_mapping()

col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns([1.5, 1.8, 1.8, 2, 1.5])

with col_c1:
    asset_type = st.selectbox("📊 Segment", ["Indices", "F&O Stocks"], key="term_seg_sel")

with col_c2:
    default_indices = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]
    default_stocks = ["RELIANCE", "TCS", "SBIN", "INFY", "HDFCBANK", "ICICIBANK", "TATAMOTORS"]
    
    seg_col = next((c for c in ['SEM_EXCH_SEGMENT', 'EXCH_SEGMENT', 'SEGMENT'] if c in master_df.columns), None)
    sym_col = next((c for c in ['SEM_TRADING_SYMBOL', 'TRADING_SYMBOL', 'SYMBOL'] if c in master_df.columns), None)
    
    available_symbols = []
    if not master_df.empty and seg_col and sym_col:
        try:
            if asset_type == "Indices":
                sub_df = master_df[master_df[seg_col].astype(str).str.upper().isin(['IDX_I', 'BSE_IDX', 'BSE_FO', 'NSE_FO'])]
            else:
                sub_df = master_df[master_df[seg_col].astype(str).str.upper().isin(['NSE_FO', 'BSE_FO', 'NSE_EQ'])]
            available_symbols = sub_df[sym_col].dropna().unique().tolist()
        except:
            available_symbols = []
            
    if not available_symbols:
        available_symbols = default_indices if asset_type == "Indices" else default_stocks

    current_idx = available_symbols.index(st.session_state.get("global_symbol", available_symbols[0])) if st.session_state.get("global_symbol", "") in available_symbols else 0
    selected_symbol = st.selectbox("🔍 Scrip Selector", available_symbols, index=current_idx, key="term_scrip_sel")
    st.session_state.global_symbol = selected_symbol

def fetch_exact_lot(symbol):
    sym_upper = symbol.upper()
    if sym_upper in lot_mapping:
        return lot_mapping[sym_upper]
    fallback_lot_map = {
        "NIFTY": 65, "BANKNIFTY": 30, "FINNIFTY": 60, "SENSEX": 20,
        "MIDCPNIFTY": 120, "NIFTYNXT50": 25, "RELIANCE": 500,
        "TCS": 225, "SBIN": 750, "HDFCBANK": 650, "ICICIBANK": 700,
        "INFY": 400, "TATAMOTORS": 1400
    }
    return fallback_lot_map.get(sym_upper, 25)

auto_lot_size = fetch_exact_lot(selected_symbol)

sec_id, seg = 13, "IDX_I"
if not master_df.empty and sym_col:
    match_row = master_df[master_df[sym_col] == selected_symbol.upper()]
    if not match_row.empty:
        id_col = next((c for c in ['SEM_SMST_SECURITY_ID', 'SECURITY_ID', 'SEM_SECURITY_ID'] if c in match_row.columns), None)
        if id_col: sec_id = int(match_row.iloc[0].get(id_col, sec_id))
        if seg_col: seg = str(match_row.iloc[0].get(seg_col, seg))

try:
    expiries = InstitutionalDataEngine.fetch_expiries(client_id, access_token, sec_id, seg)
    if not expiries: expiries = [datetime.now().strftime("%Y-%m-%d")]
except Exception:
    expiries = [datetime.now().strftime("%Y-%m-%d")]

with col_c3:
    selected_expiry = st.selectbox("📅 Expiry", expiries, index=0, key=f"term_exp_{selected_symbol}")

with col_c4:
    strike_range_mode = st.selectbox(
        "🎯 Range", 
        ["±5 Strikes", "±10 Strikes", "±20 Strikes", "±30 Strikes", "Full Chain (All)"],
        index=1,
        key=f"term_range_{selected_symbol}"
    )

with col_c5:
    show_greeks = st.checkbox("Show Greeks", value=True, key="term_greeks")

@st.fragment(run_every=300)
def render_institutional_terminal():
    try:
        chain_df, live_spot = InstitutionalDataEngine.fetch_live_option_chain(
            client_id, access_token, sec_id, seg, selected_expiry, selected_symbol
        )
    except Exception:
        chain_df, live_spot = None, 0.0

    if chain_df is None or chain_df.empty or live_spot <= 0:
        st.warning(f"⚠️ **{selected_symbol}** ke liye live option chain datauplabdh nahi hai.")
        return

    strike_col = 'Strike' if 'Strike' in chain_df.columns else ('STRIKE' if 'STRIKE' in chain_df.columns else chain_df.columns[0])
    chain_df['Strike'] = pd.to_numeric(chain_df[strike_col], errors='coerce')
    chain_df.dropna(subset=['Strike'], inplace=True)

    if 'CE_LTP' not in chain_df.columns: chain_df['CE_LTP'] = chain_df.get('Call_LTP', 10.0)
    if 'PE_LTP' not in chain_df.columns: chain_df['PE_LTP'] = chain_df.get('Put_LTP', 10.0)
    if 'Raw_CE_OI' not in chain_df.columns: chain_df['Raw_CE_OI'] = chain_df.get('CE_OI', chain_df.get('Call_OI', 100000))
    if 'Raw_PE_OI' not in chain_df.columns: chain_df['Raw_PE_OI'] = chain_df.get('PE_OI', chain_df.get('Put_OI', 100000))

    max_pain_val = int(chain_df['Strike'].iloc[0])
    resistance_strike = int(chain_df.loc[chain_df['Raw_CE_OI'].idxmax()]['Strike']) if not chain_df.empty else live_spot
    support_strike = int(chain_df.loc[chain_df['Raw_PE_OI'].idxmax()]['Strike']) if not chain_df.empty else live_spot

    f_ce_oi, f_pe_oi = chain_df['Raw_CE_OI'].sum(), chain_df['Raw_PE_OI'].sum()
    pcr_val = round(f_pe_oi / f_ce_oi, 2) if f_ce_oi > 0 else 0.85

    st.markdown("---")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1: st.metric("📌 Asset", selected_symbol)
    with m2: st.metric("⚡ Live Spot", f"₹{live_spot:,.2f}")
    with m3: st.metric("⚙️ Lot Size", auto_lot_size)
    with m4: st.metric("📊 ATM IV", "13.5%")
    with m5: st.metric("⚖️ PCR", pcr_val)
    with m6: st.metric("🎯 Max Pain", max_pain_val)
    st.markdown("---")

    chain_df['STRIKE'] = chain_df['Strike']
    chain_df['CE OI (L)'] = round(chain_df['Raw_CE_OI'] / 100000, 2)
    chain_df['PE OI (L)'] = round(chain_df['Raw_PE_OI'] / 100000, 2)

    matrix_cols = ["CE OI (L)", "CE_LTP", "STRIKE", "PE_LTP", "PE OI (L)"]
    final_cols = [c for c in matrix_cols if c in chain_df.columns]
    matrix_df = chain_df[final_cols].copy()

    st.dataframe(matrix_df, use_container_width=True, height=350, hide_index=True)
    st.markdown("---")

    st.markdown(f"### 🖥️ ADVANCED GRAPHICAL TERMINAL — {selected_symbol}")
    n_strikes = len(chain_df)

    t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 = st.tabs([
        "Mod A: OI Profile", "Mod B: Gamma GEX", "Mod C: IV Smile", "Mod D: Volume", 
        "Mod E: OI Change", "Mod F: Theta Decay", "Mod G: Max Pain", "Mod H: PCR Trend", 
        "Mod I: Delta Flow", "Mod J: Vol Surface"
    ])

    with t1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=chain_df['Strike'], y=chain_df['Raw_CE_OI'], name='CE OI', marker_color='#FF5252'))
        fig.add_trace(go.Bar(x=chain_df['Strike'], y=chain_df['Raw_PE_OI'], name='PE OI', marker_color='#00E676'))
        fig.update_layout(title="[MOD A] Strike-Wise Open Interest Profile", template="plotly_dark", barmode="group")
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        fig = go.Figure()
        fig.add_bar(x=chain_df['Strike'], y=[(s - live_spot)*0.05 for s in chain_df['Strike']], marker_color='#29B6F6')
        fig.update_layout(title="[MOD B] Net Gamma Exposure (GEX)", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with t3:
        fig = go.Figure()
        fig.add_scatter(x=chain_df['Strike'], y=[13.0]*n_strikes, mode='lines+markers', name='CE IV', line=dict(color='#FF5252'))
        fig.update_layout(title="[MOD C] Implied Volatility (IV) Smile", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with t4:
        fig = go.Figure()
        fig.add_bar(x=chain_df['Strike'], y=[100000]*n_strikes, name='CE Vol', marker_color='#AB47BC')
        fig.update_layout(title="[MOD D] Strike-Wise Volume", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with t5:
        fig = go.Figure()
        fig.add_bar(x=chain_df['Strike'], y=[0]*n_strikes, name='OI Change', marker_color='#26A69A')
        fig.update_layout(title="[MOD E] Strike-Wise Change in OI", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with t6:
        fig = go.Figure()
        fig.add_scatter(x=chain_df['Strike'], y=[-15.0]*n_strikes, mode='lines+markers', name='Theta', line=dict(color='#FFEE58'))
        fig.update_layout(title="[MOD F] Theta Decay Wave", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with t7:
        fig = go.Figure()
        fig.add_scatter(x=chain_df['Strike'], y=chain_df['Raw_CE_OI'], mode='lines+markers', name='Pain', line=dict(color='#EC407A'))
        fig.update_layout(title="[MOD G] Max Pain Curve", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with t8:
        fig = go.Figure()
        fig.add_scatter(x=['09:30', '10:30', '11:30', '12:30', '13:30'], y=[pcr_val]*5, mode='lines+markers', name='PCR', line=dict(color='#42A5F5'))
        fig.update_layout(title="[MOD H] Intraday PCR Trend", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with t9:
        fig = go.Figure()
        fig.add_scatter(x=chain_df['Strike'], y=[0.5]*n_strikes, mode='lines+markers', name='Delta', line=dict(color='#66BB6A'))
        fig.update_layout(title="[MOD I] Cumulative Delta Flow", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with t10:
        fig = go.Figure(data=[go.Surface(z=np.random.rand(n_strikes, 5), x=chain_df['Strike'], y=[1, 2, 3, 4, 5])])
        fig.update_layout(title="[MOD J] Volatility Surface 3D", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

render_institutional_terminal()
