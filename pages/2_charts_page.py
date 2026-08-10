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

st.set_page_config(page_title="Institutional Quant Terminal Pro", page_icon="⚡", layout="wide")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path: sys.path.append(ROOT_DIR)

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
            except Exception: return pd.DataFrame()
        @staticmethod
        def fetch_expiries(c, a, s, seg):
            today = datetime.now()
            days_to_thu = (3 - today.weekday() + 7) % 7
            if days_to_thu == 0: days_to_thu = 7
            next_thu = today + timedelta(days=days_to_thu)
            return [(next_thu + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(4)]
        @staticmethod
        def fetch_live_option_chain(c, a, s, seg, exp, sym): return None, 0.0

from utils import calculate_max_pain, calculate_advanced_metrics, get_buildup

# Styling
st.markdown("""
<style>
    .main { background-color: #0e1117; color: #f8fafc; }
    [data-testid="stDataFrame"] { border: 1px solid #30363d; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown("## ⚡ Institutional Quant Terminal Pro")
st.markdown("---")

if "client_id" not in st.session_state: st.session_state.client_id = ""
client_id = st.session_state.client_id
access_token = st.session_state.access_token

@st.cache_data(ttl=3600)
def get_master_df(): return InstitutionalDataEngine.load_scrip_master()
master_df = get_master_df()

# --- CONTROLS ---
col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns([1.5, 1.8, 1.8, 2, 1.5])
with col_c1: asset_type = st.selectbox("📊 Segment", ["Indices", "F&O Stocks"])
with col_c2: 
    available_symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"]
    selected_symbol = st.selectbox("🔍 Scrip Selector", available_symbols)
with col_c3: selected_expiry = st.selectbox("📅 Expiry", ["2026-08-11", "2026-08-20"])
with col_c4: strike_range_mode = st.selectbox("🎯 Range", ["±10 Strikes", "Full Chain"])
with col_c5: show_greeks = st.checkbox("Show Greeks", True)

# --- TERMINAL ENGINE ---
@st.fragment(run_every=300)
def render_institutional_terminal():
    chain_df, live_spot = InstitutionalDataEngine.fetch_live_option_chain(client_id, access_token, 13, "IDX_I", selected_expiry, selected_symbol)
    
    if chain_df is None or chain_df.empty:
        st.warning("⚠️ लाइव ऑप्शन चैन डेटा प्राप्त नहीं हो पा रहा है। कृपया अपने API कनेक्शन की जाँच करें।")
        return

    # सुरक्षित कॉलम मैपिंग (KeyError से बचाने के लिए)
    strike_col = next((c for c in ['Strike', 'STRIKE', 'strike'] if c in chain_df.columns), chain_df.columns[0])
    chain_df['Strike'] = pd.to_numeric(chain_df[strike_col], errors='coerce')
    chain_df.dropna(subset=['Strike'], inplace=True)
    chain_df.sort_values(by='Strike', inplace=True)

    # OI कॉलम मैपिंग सुरक्षित करें
    ce_oi_col = next((c for c in ['Raw_CE_OI', 'CE_OI', 'Call_OI', 'CE OI'] if c in chain_df.columns), None)
    pe_oi_col = next((c for c in ['Raw_PE_OI', 'PE_OI', 'Put_OI', 'PE OI'] if c in chain_df.columns), None)
    
    chain_df['Raw_CE_OI'] = chain_df[ce_oi_col] if ce_oi_col else 100000
    chain_df['Raw_PE_OI'] = chain_df[pe_oi_col] if pe_oi_col else 100000

    # मेट्रिक्स कैलकुलेट करें
    chain_df = calculate_advanced_metrics(chain_df, live_spot, 65)
    
    # रेंज फिल्टर
    c_idx = (chain_df['Strike'] - live_spot).abs().idxmin()
    disp_df = chain_df.iloc[max(0, c_idx-10):min(len(chain_df), c_idx+11)].copy() if "±10" in strike_range_mode else chain_df

    # Display Chain DataFrame
    st.dataframe(disp_df, use_container_width=True)

    # --- SENSITIVE INSTITUTIONAL CHARTS ---
    if HAS_PLOTLY:
        st.markdown("---")
        st.markdown("### 📈 Institutional Sensitive Analytics")
        tab1, tab2, tab3 = st.tabs(["📊 OI Distribution", "⚡ Net GEX (Flip Zone)", "💰 Liquidity Concentration"])

        with tab1:
            fig_oi = go.Figure()
            fig_oi.add_trace(go.Bar(x=disp_df['Strike'], y=disp_df['Raw_CE_OI'], name='Call OI', marker_color='#ef4444'))
            fig_oi.add_trace(go.Bar(x=disp_df['Strike'], y=disp_df['Raw_PE_OI'], name='Put OI', marker_color='#22c55e'))
            fig_oi.update_layout(barmode='group', plot_bgcolor='#0e1117', paper_bgcolor='#0e1117', font=dict(color='#f8fafc'), xaxis_title="Strike", yaxis_title="Open Interest")
            st.plotly_chart(fig_oi, use_container_width=True)

        with tab2:
            net_gex = disp_df.get('CE GEX (Cr)', 0) - disp_df.get('PE GEX (Cr)', 0)
            fig_gex = go.Figure()
            fig_gex.add_trace(go.Bar(x=disp_df['Strike'], y=net_gex, marker_color=np.where(net_gex > 0, '#ef4444', '#22c55e')))
            fig_gex.add_hline(y=0, line_color="white")
            fig_gex.update_layout(plot_bgcolor='#0e1117', paper_bgcolor='#0e1117', font=dict(color='#f8fafc'), xaxis_title="Strike", yaxis_title="Net GEX (Cr)")
            st.plotly_chart(fig_gex, use_container_width=True)

        with tab3:
            total_liq = disp_df.get('CE Turnover (Cr)', 0) + disp_df.get('PE Turnover (Cr)', 0)
            fig_liq = go.Figure()
            fig_liq.add_trace(go.Scatter(x=disp_df['Strike'], y=total_liq, fill='tozeroy', line=dict(color='#f59e0b', width=3)))
            fig_liq.update_layout(plot_bgcolor='#0e1117', paper_bgcolor='#0e1117', font=dict(color='#f8fafc'), xaxis_title="Strike", yaxis_title="Total Turnover (Cr)")
            st.plotly_chart(fig_liq, use_container_width=True)

render_institutional_terminal()
