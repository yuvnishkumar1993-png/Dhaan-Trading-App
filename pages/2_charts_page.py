import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- SAFE PATH RESOLUTION ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from utils import (
    fetch_available_expiries,
    fetch_market_option_chain, 
    calculate_max_pain, 
    calculate_advanced_metrics
)

# Page Configuration
st.set_page_config(
    page_title="Institutional Quant Terminal Pro",
    page_icon="⚡",
    layout="wide"
)

st.markdown("## ⚡ Institutional Quant Terminal Pro")
st.markdown("---")

master_dict = {
    "NIFTY": {"sec_id": 13, "seg": "IDX_I", "lot": 65},
    "BANKNIFTY": {"sec_id": 25, "seg": "IDX_I", "lot": 15},
    "FINNIFTY": {"sec_id": 27, "seg": "IDX_I", "lot": 25},
    "SENSEX": {"sec_id": 51, "seg": "BSE_IDX", "lot": 10},
    "RELIANCE": {"sec_id": 2885, "seg": "NSE_EQ", "lot": 250}
}

# --- GLOBAL CONTROLS ---
col_h1, col_h2, col_h3, col_h4 = st.columns([2, 2, 2, 2])
with col_h1:
    selected_symbol = st.selectbox("📌 Asset", list(master_dict.keys()), key="sel_asset")

cfg = master_dict.get(selected_symbol, {"sec_id": 13, "seg": "IDX_I", "lot": 65})

# ऑटोमैटिक एक्सपायरी फेच करना और सॉर्ट करना
expiries = fetch_available_expiries(client_id="", access_token="", sec_id=cfg["sec_id"], seg=cfg["seg"])

with col_h2:
    # हमेशा सबसे पहली (सबसे नजदीक की) एक्सपायरी को ऑटो-सेलेक्ट करना (index=0)
    selected_expiry = st.selectbox("📅 Expiry", expiries, index=0, key=f"sel_exp_{selected_symbol}")

with col_h3:
    active_page = st.selectbox("📑 Terminal Page", ["Page 1: Core Option Chain", "Page 2: Sensibull-Style Analytics & Graphs"], key="sel_page")

with col_h4:
    lot_size = st.number_input("⚙️ Lot Size", min_value=1, value=int(cfg["lot"]), key="sel_lot")

# --- FETCH REAL / DYNAMIC DATA FROM UTILS ---
raw_df, live_spot = fetch_market_option_chain(
    client_id="", access_token="", 
    sec_id=cfg["sec_id"], seg=cfg["seg"], 
    expiry=selected_expiry, symbol=selected_symbol
)

if raw_df is not None and not raw_df.empty:
    chain_df = calculate_advanced_metrics(raw_df, live_spot, lot_size)
else:
    chain_df = pd.DataFrame()

# ==========================================
# PAGE 1: CORE OPTION CHAIN TABLE
# ==========================================
if "Page 1" in active_page:
    st.markdown(f"### 📊 Page 1: Core Option Chain (Spot: ₹{live_spot:,.2f})")
    st.markdown("---")
    if not chain_df.empty:
        display_cols = ['Strike', 'Raw_CE_OI', 'CE_LTP', 'CE_IV', 'CE Delta', 'Gamma', 'PE_IV', 'PE_LTP', 'Raw_PE_OI']
        st.dataframe(chain_df[[c for c in display_cols if c in chain_df.columns]], use_container_width=True, height=600, hide_index=True)
    else:
        st.warning("No data available.")

# ========================================================
# PAGE 2: SENSIBULL-STYLE ADVANCED GRAPH DASHBOARD
# ========================================================
elif "Page 2" in active_page:
    st.markdown(f"### 🎯 Page 2: Sensibull-Style Analytics (Spot: ₹{live_spot:,.2f})")
    st.markdown("---")
    
    if not chain_df.empty:
        total_call_oi = chain_df['Raw_CE_OI'].sum()
        total_put_oi = chain_df['Raw_PE_OI'].sum()
        pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0
        
        max_pain_strike = calculate_max_pain(chain_df, live_spot)

        max_call_row = chain_df.loc[chain_df['Raw_CE_OI'].idxmax()]
        max_put_row = chain_df.loc[chain_df['Raw_PE_OI'].idxmax()]
        
        immediate_resistance = int(max_call_row['Strike'])
        immediate_support = int(max_put_row['Strike'])

        # Top Macro KPI Cards
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Live PCR", pcr, delta="Bullish" if pcr > 1.1 else "Bearish")
        with m2: st.metric("Max Pain Strike", f"{max_pain_strike:,}")
        with m3: st.metric("Immediate Resistance", f"{immediate_resistance:,}", delta="Max Call OI")
        with m4: st.metric("Immediate Support", f"{immediate_support:,}", delta="Max Put OI")
        
        st.markdown("---")

        # Filter nearby strikes for crisp plotting (±12 strikes around live spot)
        chain_df['Dist'] = abs(chain_df['Strike'] - live_spot)
        center_idx = chain_df['Dist'].idxmin()
        plot_df = chain_df.iloc[max(0, center_idx-12):min(len(chain_df), center_idx+13)].copy()

        # --- GRAPH 1: Open Interest Distribution Chart ---
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
            height=420
        )
        st.plotly_chart(fig_oi, use_container_width=True)

        st.markdown("---")

        # --- GRAPH 2: Implied Volatility (IV) Smile / Skew Curve ---
        st.markdown("#### 📉 2. Implied Volatility (IV) Smile & Skew Curve")
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
            height=400
        )
        st.plotly_chart(fig_iv, use_container_width=True)
    else:
        st.warning("No data found for graphing.")
