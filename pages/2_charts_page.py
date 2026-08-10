import sys
import os

# रूट फोल्डर को सिस्टम पाथ में जोड़ें ताकि utils.py आसानी से इम्पोर्ट हो सके
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from utils import (
    get_option_chain_data,
    calculate_max_pain,
    detect_oi_spurt,
    calculate_strategy_payoff,
    get_multi_expiry_matrix
)

st.title("📈 Advanced Charts & Graphics Analyzer Dashboard")
st.markdown("लाइव कैंडलस्टिक चार्ट्स, ऑप्शन चेन ग्राफिक्स, मैक्स पेन और स्ट्रैटेजी पेऑफ का संपूर्ण डैशबोर्ड।")

# Sidebar Controls
st.sidebar.header("Chart & Analyzer Settings")
symbol = st.sidebar.selectbox("Select Index / Stock", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
timeframe = st.sidebar.selectbox("Select Timeframe", ["1m", "5m", "15m", "1h", "1D"])

expiries = get_multi_expiry_matrix()
selected_expiry = st.sidebar.selectbox("Select Expiry", expiries)

# Fetch Data from utils
with st.spinner("Fetching Data..."):
    df_chain = get_option_chain_data()

# Tabs for Organization
tab1, tab2, tab3 = st.tabs(["🕯️ Live Candlestick Chart", "📊 Graphics & OI Analyzer", "🧮 Strategy Payoff Simulator"])

with tab1:
    st.subheader(f"Price Action Chart for **{symbol}** ({timeframe})")
    
    @st.cache_data(ttl=10)
    def load_chart_data(sym, tf):
        data = {
            'Time': pd.date_range(start='2026-08-11 09:15:00', periods=50, freq='5min'),
            'Open': [24500 + i*5 for i in range(50)],
            'High': [24520 + i*5 for i in range(50)],
            'Low': [24490 + i*5 for i in range(50)],
            'Close': [24510 + i*5 for i in range(50)],
        }
        return pd.DataFrame(data)

    df_chart = load_chart_data(symbol, timeframe)

    if not df_chart.empty:
        fig_candle = go.Figure(data=[go.Candlestick(
            x=df_chart['Time'],
            open=df_chart['Open'],
            high=df_chart['High'],
            low=df_chart['Low'],
            close=df_chart['Close'],
            name="Candles"
        )])
        fig_candle.update_layout(
            template="plotly_dark",
            xaxis_title="Time",
            yaxis_title="Price (INR)",
            height=550
        )
        st.plotly_chart(fig_candle, use_container_width=True)
    else:
        st.warning("⚠️ Chart data not available.")

with tab2:
    st.subheader("📊 Option Chain Graphics, Max Pain & OI Spurt")
    if df_chain is not None and not df_chain.empty:
        total_ce_oi = df_chain['CE_OpenInterest'].sum() if 'CE_OpenInterest' in df_chain.columns else 0
        total_pe_oi = df_chain['PE_OpenInterest'].sum() if 'PE_OpenInterest' in df_chain.columns else 0
        pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0
        max_pain = calculate_max_pain(df_chain)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(label="Total CE OI", value=f"{total_ce_oi:,}")
        c2.metric(label="Total PE OI", value=f"{total_pe_oi:,}")
        c3.metric(label="PCR", value=pcr, delta="Bullish" if pcr > 1.2 else "Bearish" if pcr < 0.8 else "Neutral")
        c4.metric(label="Max Pain Strike", value=str(max_pain) if max_pain else "N/A")

        st.markdown("---")

        if 'StrikePrice' in df_chain.columns:
            fig_oi = go.Figure(data=[
                go.Bar(name='Call OI (CE)', x=df_chain['StrikePrice'], y=df_chain['CE_OpenInterest'], marker_color='#EF553B'),
                go.Bar(name='Put OI (PE)', x=df_chain['StrikePrice'], y=df_chain['PE_OpenInterest'], marker_color='#00CC96')
            ])
            if max_pain:
                fig_oi.add_vline(x=max_pain, line_dash="dash", line_color="yellow", annotation_text=f"Max Pain: {max_pain}")

            fig_oi.update_layout(barmode='group', template='plotly_dark', title="CE vs PE Open Interest", height=500)
            st.plotly_chart(fig_oi, use_container_width=True)

        st.markdown("### 🚨 Real-time OI Spurt")
        spurt_df = detect_oi_spurt(df_chain, threshold=50000)
        if not spurt_df.empty:
            st.dataframe(spurt_df, use_container_width=True)
        else:
            st.info("ℹ️ कोई बड़ा OI Spurt डिटेक्ट नहीं हुआ है।")
    else:
        st.warning("⚠️ ऑप्शन चेन डेटा उपलब्ध नहीं है।")

with tab3:
    st.subheader("🧮 Strategy Payoff Calculator")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        strat_type = st.selectbox("Select Strategy", ["Bull Call Spread", "Long Straddle"])
        max_pain_val = calculate_max_pain(df_chain) if df_chain is not None and not df_chain.empty else 24500
        strike_atm = st.number_input("Base Strike Price (ATM)", value=int(max_pain_val) if max_pain_val else 24500, step=50)
        strike_spread = st.number_input("Second Strike / Offset", value=strike_atm + 200, step=50)
    with col_s2:
        prem_1 = st.number_input("Premium 1 (Buy)", value=120.0, step=5.0)
        prem_2 = st.number_input("Premium 2 (Sell)", value=60.0, step=5.0)

    spot_range = np.linspace(strike_atm - 500, strike_atm + 500, 100)
    payoff_df = calculate_strategy_payoff(strat_type, strike_atm, strike_spread, prem_1, prem_2, spot_range)

    fig_pnl = go.Figure()
    fig_pnl.add_trace(go.Scatter(x=payoff_df['SpotPrice'], y=payoff_df['PnL'], mode='lines', name='Net PnL', line=dict(color='cyan', width=3)))
    fig_pnl.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_pnl.update_layout(template='plotly_dark', title=f"Payoff: {strat_type}", xaxis_title="Spot Price", yaxis_title="PnL (INR)", height=450)
    st.plotly_chart(fig_pnl, use_container_width=True)
