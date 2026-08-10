import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# utils.py से फंक्शन्स इम्पोर्ट करना
from utils import (
    get_option_chain_data, 
    calculate_max_pain, 
    calculate_advanced_metrics
)

# Page Configuration
st.set_page_config(
    page_title="Institutional Quant Terminal Pro",
    page_icon="⚡",
    layout="wide"
)

# Professional Styling Injection
st.markdown("""
<style>
    .main { background-color: #0e1117; color: #f8fafc; }
    div[data-testid="stHorizontalBlock"] > div { align-items: center; }
</style>
""", unsafe_allow_html=True)

st.markdown("## ⚡ Institutional Quant Terminal Pro")
st.markdown("---")

# --- GLOBAL CONTROLS ---
col_h1, col_h2, col_h3 = st.columns([2, 2, 2])
with col_h1:
    selected_symbol = st.selectbox("📌 Asset", ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "RELIANCE"])
with col_h2:
    active_page = st.selectbox("📑 Terminal Page", ["Page 1: Core Option Chain", "Page 2: Sensibull-Style Analytics & Graphs"])
with col_h3:
    lot_size = st.number_input("⚙️ Lot Size", min_value=1, value=65)

# --- DATA FETCHING (FROM UTILS) ---
raw_df = get_option_chain_data()
live_spot = 24500.0  # मान लेते हैं करेंट स्पॉट प्राइस 24500 है

if raw_df is not None and not raw_df.empty:
    chain_df = calculate_advanced_metrics(raw_df, live_spot, lot_size)
else:
    chain_df = pd.DataFrame()

# ==========================================
# PAGE 1: CORE OPTION CHAIN TABLE
# ==========================================
if "Page 1" in active_page:
    st.markdown("### 📊 Page 1: Core Option Chain & Price Action Matrix")
    st.markdown("---")
    if not chain_df.empty:
        display_cols = ['Strike', 'CE_OpenInterest', 'CE_LTP', 'CE_IV', 'CE Delta', 'Gamma', 'PE_IV', 'PE_LTP', 'PE_OpenInterest']
        st.dataframe(chain_df[[c for c in display_cols if c in chain_df.columns]], use_container_width=True, height=600, hide_index=True)
    else:
        st.warning("No data available.")

# ========================================================
# PAGE 2: SENSIBULL-STYLE ADVANCED GRAPH DASHBOARD
# ========================================================
elif "Page 2" in active_page:
    st.markdown("### 🎯 Page 2: Sensibull-Style Advanced OI & Analytics Graphs")
    st.markdown("---")
    
    if not chain_df.empty:
        total_call_oi = chain_df['Raw_CE_OI'].sum()
        total_put_oi = chain_df['Raw_PE_OI'].sum()
        pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0
        
        # Max Pain calculation from utils
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

        # --- GRAPH 1: Open Interest Distribution Chart ---
        st.markdown("#### 📊 1. Strike-wise Open Interest (OI) Distribution Chart")
        fig_oi = go.Figure()
        fig_oi.add_trace(go.Bar(
            x=chain_df['Strike'], y=chain_df['Raw_CE_OI'] / 100000,
            name='Call OI (Resistance)', marker_color='#ef4444'
        ))
        fig_oi.add_trace(go.Bar(
            x=chain_df['Strike'], y=chain_df['Raw_PE_OI'] / 100000,
            name='Put OI (Support)', marker_color='#22c55e'
        ))
        fig_oi.add_vline(x=live_spot, line_dash="dash", line_color="#fbbf24", annotation_text=f"Spot: {live_spot}")
        fig_oi.update_layout(
            barmode='group', template='plotly_dark',
            xaxis_title="Strike Price", yaxis_title="Open Interest (in Lakhs)",
            height=420
        )
        st.plotly_chart(fig_oi, use_container_width=True)

        st.markdown("---")

        # --- GRAPH 2: Implied Volatility (IV) Smile / Skew Chart ---
        st.markdown("#### 📉 2. Implied Volatility (IV) Smile & Skew Curve")
        fig_iv = go.Figure()
        fig_iv.add_trace(go.Scatter(
            x=chain_df['Strike'], y=chain_df['CE_IV'],
            mode='lines+markers', name='Call IV', line=dict(color='#ef4444', width=2)
        ))
        fig_iv.add_trace(go.Scatter(
            x=chain_df['Strike'], y=chain_df['PE_IV'],
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
