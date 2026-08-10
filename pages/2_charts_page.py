import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
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
            today = datetime.now()
            days_to_thu = (3 - today.weekday() + 7) % 7
            if days_to_thu == 0: days_to_thu = 7
            next_thu = today + timedelta(days=days_to_thu)
            return [(next_thu + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(4)]
        @staticmethod
        def fetch_live_option_chain(c, a, s, seg, exp, sym):
            return None, 0.0

# Import modular backend functions from utils
try:
    from utils import calculate_max_pain, calculate_advanced_metrics, get_buildup
except ImportError:
    st.error("❌ `utils.py` could not be imported. Please verify root directory.")
    st.stop()

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

# --- 1. CONTROLS PANEL ---
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
        "NIFTY": 65, "BANKNIFTY": 30, "FINNIFTY": 60, "SENSEX": 20, "MIDCPNIFTY": 120,
        "NIFTYNXT50": 25, "RELIANCE": 500, "TCS": 225, "SBIN": 750, "HDFCBANK": 650,
        "ICICIBANK": 700, "INFY": 400, "TATAMOTORS": 1400
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


# --- 3. AUTOMATIC REFRESH ENGINE (`st.fragment`) ---
@st.fragment(run_every=300)
def render_institutional_terminal():
    try:
        chain_df, live_spot = InstitutionalDataEngine.fetch_live_option_chain(
            client_id, access_token, sec_id, seg, selected_expiry, selected_symbol
        )
    except Exception:
        chain_df, live_spot = None, 0.0

    if chain_df is None or chain_df.empty or live_spot <= 0:
        st.warning(f"⚠️ **{selected_symbol}** के लिए लाइव ऑप्शन चैन डेटा प्राप्त नहीं हो पा रहा है। कृपया अपने Dhan API टोकन की जाँच करें।")
        return

    strike_col = 'Strike' if 'Strike' in chain_df.columns else ('STRIKE' if 'STRIKE' in chain_df.columns else chain_df.columns[0])
    chain_df['Strike'] = pd.to_numeric(chain_df[strike_col], errors='coerce')
    chain_df.dropna(subset=['Strike'], inplace=True)
    
    # स्ट्राइक के आधार पर सॉर्ट करना अनिवार्य है
    chain_df.sort_values(by='Strike', inplace=True)
    chain_df.reset_index(drop=True, inplace=True)

    if 'CE_LTP' not in chain_df.columns and 'Call_LTP' in chain_df.columns:
        chain_df['CE_LTP'] = chain_df['Call_LTP']
    elif 'CE_LTP' not in chain_df.columns: chain_df['CE_LTP'] = 10.0

    if 'PE_LTP' not in chain_df.columns and 'Put_LTP' in chain_df.columns:
        chain_df['PE_LTP'] = chain_df['Put_LTP']
    elif 'PE_LTP' not in chain_df.columns: chain_df['PE_LTP'] = 10.0

    if 'Raw_CE_OI' not in chain_df.columns: chain_df['Raw_CE_OI'] = chain_df.get('CE_OI', chain_df.get('Call_OI', 100000))
    if 'Raw_PE_OI' not in chain_df.columns: chain_df['Raw_PE_OI'] = chain_df.get('PE_OI', chain_df.get('Put_OI', 100000))

    max_pain_val = calculate_max_pain(chain_df, live_spot)
    resistance_strike = int(chain_df.loc[chain_df['Raw_CE_OI'].idxmax()]['Strike']) if not chain_df.empty else live_spot
    support_strike = int(chain_df.loc[chain_df['Raw_PE_OI'].idxmax()]['Strike']) if not chain_df.empty else live_spot

    # Call utility function for advanced metrics (यहीं से सारे ग्रीक्स जुड़ेंगे)
    chain_df = calculate_advanced_metrics(chain_df, live_spot, auto_lot_size)

    # Strike Filtering for Display
    chain_df['Dist'] = abs(chain_df['Strike'] - live_spot)
    c_idx = chain_df['Dist'].idxmin() if not chain_df.empty else 0
    
    if "±5" in strike_range_mode:
        disp_df = chain_df.iloc[max(0, c_idx-5):min(len(chain_df), c_idx+6)].copy()
    elif "±10" in strike_range_mode:
        disp_df = chain_df.iloc[max(0, c_idx-10):min(len(chain_df), c_idx+11)].copy()
    elif "±20" in strike_range_mode:
        disp_df = chain_df.iloc[max(0, c_idx-20):min(len(chain_df), c_idx+21)].copy()
    elif "±30" in strike_range_mode:
        disp_df = chain_df.iloc[max(0, c_idx-30):min(len(chain_df), c_idx+31)].copy()
    else:
        disp_df = chain_df.copy()

    atm_row = disp_df.loc[disp_df['Dist'].idxmin()] if not disp_df.empty else chain_df.iloc[c_idx]
    atm_iv = round((float(atm_row.get('CE_IV', 13.0)) + float(atm_row.get('PE_IV', 13.5))) / 2.0, 2)
    f_ce_oi, f_pe_oi = chain_df['Raw_CE_OI'].sum(), chain_df['Raw_PE_OI'].sum()
    pcr_val = round(f_pe_oi / f_ce_oi, 2) if f_ce_oi > 0 else 0.85

    # --- DASHBOARD METRICS BAR ---
    st.markdown("---")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1: st.metric("📌 Asset", selected_symbol)
    with m2: st.metric("⚡ Live Spot", f"₹{live_spot:,.2f}")
    with m3: st.metric("⚙️ Lot Size", auto_lot_size)
    with m4: st.metric("📊 ATM IV", f"{atm_iv}%")
    with m5: st.metric("⚖️ PCR", pcr_val, delta="Bullish" if pcr_val > 1.0 else "Bearish")
    with m6: st.metric("🎯 Max Pain", max_pain_val)
    st.markdown("---")

    with st.expander("🔍 Key Institutional Levels & Analytics (Support, Resistance, Max Pain)", expanded=False):
        col_in1, col_in2, col_in3 = st.columns(3)
        col_in1.metric("🛡️ Immediate Support (Max Put OI)", support_strike)
        col_in2.metric("🚧 Immediate Resistance (Max Call OI)", resistance_strike)
        col_in3.metric("🎯 Expected Settlement (Max Pain)", max_pain_val)

    disp_df['CE Build'] = disp_df.apply(lambda r: get_buildup(r.get('CE_Chg_OI', 0), r.get('CE_%Chg', 0)), axis=1)
    disp_df['PE Build'] = disp_df.apply(lambda r: get_buildup(r.get('PE_Chg_OI', 0), r.get('PE_%Chg', 0)), axis=1)

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

    def professional_terminal_styling(row):
        strike = row['STRIKE']
        styles = [''] * len(row)
        is_atm = abs(strike - live_spot) <= 25 or strike == atm_strike_val
        
        for i, col_name in enumerate(row.index):
            if col_name == 'STRIKE':
                if is_atm: styles[i] = 'background-color: #d97706; color: #ffffff; font-weight: bold; font-size: 14px;'
                else: styles[i] = 'background-color: #1f2937; color: #f9fafb; font-weight: bold;'
            elif 'CE' in col_name:
                styles[i] = 'background-color: #111e38; color: #e2e8f0;' if strike < live_spot else 'background-color: #0f172a; color: #94a3b8;'
            elif 'PE' in col_name:
                styles[i] = 'background-color: #381116; color: #e2e8f0;' if strike > live_spot else 'background-color: #1e1114; color: #94a3b8;'
        return styles

    styled_df = matrix_df.style.apply(professional_terminal_styling, axis=1)

    st.markdown(f"### 📊 Professional Institutional Option Chain ({strike_range_mode})")
    st.markdown("---")
    st.dataframe(styled_df, use_container_width=True, height=500, hide_index=True)

    # --- 4. VISUAL OI BUILD-UP CHART (Plotly) ---
    if HAS_PLOTLY:
        st.markdown("### 📈 Open Interest (OI) Distribution Chart")
        # ATM के आस-पास के 15 स्ट्राइक्स का डायनामिक चार्ट
        c_idx_full = chain_df['Dist'].idxmin() if not chain_df.empty else 0
        chart_df = chain_df.iloc[max(0, c_idx_full-7):min(len(chain_df), c_idx_full+8)].copy()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=chart_df['Strike'], y=chart_df['Raw_CE_OI'], name='Call OI (Resistance)', marker_color='#ef4444'))
        fig.add_trace(go.Bar(x=chart_df['Strike'], y=chart_df['Raw_PE_OI'], name='Put OI (Support)', marker_color='#22c55e'))
        fig.update_layout(
            barmode='group',
            plot_bgcolor='#0e1117',
            paper_bgcolor='#0e1117',
            font=dict(color='#f8fafc'),
            xaxis_title="Strike Price",
            yaxis_title="Open Interest",
            legend=dict(x=0, y=1.1, orientation="h")
        )
        st.plotly_chart(fig, use_container_width=True)

render_institutional_terminal()
# चार्ट्स को अलग-अलग टैब्स में दिखाएं
tab1, tab2, tab3 = st.tabs(["📊 OI Distribution", "⚡ Gamma Exposure (GEX)", "💰 Turnover Profile"])

with tab1:
    # आपका मौजूदा OI चार्ट यहाँ आएगा
    pass

with tab2:
    st.subheader("Gamma Exposure (Institutional Magnet)")
    fig_gex = go.Figure()
    fig_gex.add_trace(go.Scatter(x=disp_df['STRIKE'], y=disp_df['CE GEX (Cr)'], name='CE GEX', line=dict(color='red')))
    fig_gex.add_trace(go.Scatter(x=disp_df['STRIKE'], y=disp_df['PE GEX (Cr)'], name='PE GEX', line=dict(color='green')))
    st.plotly_chart(fig_gex, use_container_width=True)

with tab3:
    st.subheader("Volume Turnover (Liquidity Map)")
    fig_turn = go.Figure()
    fig_turn.add_trace(go.Bar(x=disp_df['STRIKE'], y=disp_df['CE Turnover (Cr)'], name='CE Turnover', marker_color='orange'))
    st.plotly_chart(fig_turn, use_container_width=True)

