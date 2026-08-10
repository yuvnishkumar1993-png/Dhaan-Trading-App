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

st.set_page_config(page_title="Graphics & Advanced Analyzer", layout="wide")

st.title("📊 Institutional Graphics & Option Analyzer")
st.markdown("ऑप्शन चेन, ओपन इंटरेस्ट स्पर्ट, मैक्स पेन और स्ट्रेटजी पेऑफ का एडवांस्ड ग्राफिकल विश्लेषण।")

# Sidebar Controls
st.sidebar.header("Analyzer Settings")
expiries = get_multi_expiry_matrix()
selected_expiry = st.sidebar.selectbox("Select Expiry", expiries)

# Fetch Data from utils
with st.spinner("Fetching Live Option Chain Data..."):
    df_chain = get_option_chain_data()

if df_chain is not None and not df_chain.empty:
    # Core Calculations
    total_ce_oi = df_chain['CE_OpenInterest'].sum() if 'CE_OpenInterest' in df_chain.columns else 0
    total_pe_oi = df_chain['PE_OpenInterest'].sum() if 'PE_OpenInterest' in df_chain.columns else 0
    pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0
    max_pain = calculate_max_pain(df_chain)

    # Top Metrics Dashboard
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total CE OI", value=f"{total_ce_oi:,}")
    with col2:
        st.metric(label="Total PE OI", value=f"{total_pe_oi:,}")
    with col3:
        st.metric(label="Put-Call Ratio (PCR)", value=pcr, delta="Bullish" if pcr > 1.2 else "Bearish" if pcr < 0.8 else "Neutral")
    with col4:
        st.metric(label="Max Pain Strike", value=str(max_pain) if max_pain else "N/A")

    st.markdown("---")

    # Tabs for Different Advanced Views
    tab1, tab2, tab3 = st.tabs(["📈 OI & Max Pain Chart", "⚡ OI Spurt / Spikes", "🧮 Strategy Payoff Simulator"])

    with tab1:
        st.subheader("Strike-wise Open Interest (CE vs PE) with Max Pain")
        if 'StrikePrice' in df_chain.columns:
            fig = go.Figure(data=[
                go.Bar(name='Call OI (CE)', x=df_chain['StrikePrice'], y=df_chain['CE_OpenInterest'], marker_color='#EF553B'),
                go.Bar(name='Put OI (PE)', x=df_chain['StrikePrice'], y=df_chain['PE_OpenInterest'], marker_color='#00CC96')
            ])
            
            if max_pain:
                fig.add_vline(x=max_pain, line_dash="dash", line_color="yellow", annotation_text=f"Max Pain: {max_pain}")

            fig.update_layout(
                barmode='group',
                template='plotly_dark',
                title=f"Open Interest Distribution ({selected_expiry})",
                xaxis_title="Strike Price",
                yaxis_title="Open Interest",
                height=550
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("⚠️ StrikePrice column missing in data.")

    with tab2:
        st.subheader("🚨 Real-time OI Spurt & Volume Anomalies")
        spurt_df = detect_oi_spurt(df_chain, threshold=50000)
        if not spurt_df.empty:
            st.dataframe(spurt_df, use_container_width=True)
        else:
            st.info("ℹ️ वर्तमान में किसी बड़े OI Spurt या अनवाइंडिंग का डिटेक्ट नहीं हुआ है।")

    with tab3:
        st.subheader("📊 Interactive Options Strategy Payoff Calculator")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            strat_type = st.selectbox("Select Strategy", ["Bull Call Spread", "Long Straddle"])
            strike_atm = st.number_input("Base Strike Price (ATM)", value=int(max_pain) if max_pain else 24500, step=50)
            strike_spread = st.number_input("Second Strike / Spread Offset", value=strike_atm + 200, step=50)
        with col_s2:
            prem_1 = st.number_input("Premium 1 (Buy/Long)", value=120.0, step=5.0)
            prem_2 = st.number_input("Premium 2 (Sell/Short)", value=60.0, step=5.0)

        spot_min = strike_atm - 500
        spot_max = strike_atm + 500
        spot_range = np.linspace(spot_min, spot_max, 100)

        payoff_df = calculate_strategy_payoff(strat_type, strike_atm, strike_spread, prem_1, prem_2, spot_range)

        fig_pnl = go.Figure()
        fig_pnl.add_trace(go.Scatter(x=payoff_df['SpotPrice'], y=payoff_df['PnL'], mode='lines', name='Net PnL', line=dict(color='cyan', width=3)))
        fig_pnl.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_pnl.update_layout(
            template='plotly_dark',
            title=f"Payoff Diagram: {strat_type}",
            xaxis_title="Spot Price at Expiry",
            yaxis_title="Profit / Loss (INR)",
            height=450
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

else:
    st.warning("⚠️ ऑप्शन चेन डेटा उपलब्ध नहीं है। कृपया अपनी `utils.py` या एपीआई कनेक्शन की जांच करें।")
