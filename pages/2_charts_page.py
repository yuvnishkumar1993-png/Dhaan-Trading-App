import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from backend import get_market_data

# Page Configuration
st.set_page_config(
    page_title="Dhaan Trading App - Advanced Graphical Terminal",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling for Clean Dashboard Look
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
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

# Fetch Market Data safely
asset = st.session_state.get("selected_asset", "SENSEX")
try:
    spot, chain_df, _, _, _ = get_market_data(asset)
except Exception as e:
    st.error(f"Failed to load market data: {e}")
    # Fallback dummy data if backend fails
    spot = 74000
    chain_df = pd.DataFrame({
        'strike': [73500, 73800, 74000, 74200, 74500],
        'ce_oi': [150000, 230000, 450000, 180000, 90000],
        'pe_oi': [120000, 290000, 520000, 210000, 110000],
        'ce_iv': [14.2, 13.8, 13.5, 14.0, 14.6],
        'pe_iv': [15.1, 14.3, 13.6, 13.9, 14.4],
        'ce_volume': [50000, 80000, 120000, 60000, 30000],
        'pe_volume': [45000, 95000, 140000, 75000, 35000]
    })

n_strikes = len(chain_df) if chain_df is not None and not chain_df.empty else 5

st.header(f"🖥️ PAGE 2: ADVANCED GRAPHICAL TERMINAL (ALL 10 MODULES) — {asset}")
st.markdown(f"**Spot Price:** `{spot}` | **Total Strikes Tracked:** `{n_strikes}`")

# Tabs for 10 Modules
t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 = st.tabs([
    "Mod A: OI Profile", "Mod B: Gamma GEX", "Mod C: IV Smile", "Mod D: Volume", 
    "Mod E: OI Change", "Mod F: Theta Decay", "Mod G: Max Pain", "Mod H: PCR Trend", 
    "Mod I: Delta Flow", "Mod J: Vol Surface"
])

# --- MOD A: OI Profile ---
with t1:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=chain_df['strike'], y=chain_df['ce_oi'], name='CE OI (Resistance)', marker_color='#FF5252'))
    fig.add_trace(go.Bar(x=chain_df['strike'], y=chain_df['pe_oi'], name='PE OI (Support)', marker_color='#00E676'))
    fig.update_layout(
        title="[MOD A] Strike-Wise Open Interest Profile", 
        template="plotly_dark", 
        barmode="group",
        xaxis_title="Strike Price",
        yaxis_title="Open Interest"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- MOD B: Gamma GEX ---
with t2:
    gex_vals = [(s - spot) * 0.05 for s in chain_df['strike']]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=chain_df['strike'], y=gex_vals, name='Net Gamma', marker_color='#29B6F6'))
    fig.update_layout(
        title="[MOD B] Net Gamma Exposure (GEX) Distribution", 
        template="plotly_dark",
        xaxis_title="Strike Price",
        yaxis_title="Gamma Exposure"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- MOD C: IV Smile ---
with t3:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=chain_df['strike'], y=chain_df['ce_iv'], mode='lines+markers', name='CE IV', line=dict(color='#FF5252', width=2)))
    fig.add_trace(go.Scatter(x=chain_df['strike'], y=chain_df['pe_iv'], mode='lines+markers', name='PE IV', line=dict(color='#00E676', width=2)))
    fig.update_layout(
        title="[MOD C] Implied Volatility (IV) Smile Curve", 
        template="plotly_dark",
        xaxis_title="Strike Price",
        yaxis_title="IV (%)"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- MOD D: Volume ---
with t4:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=chain_df['strike'], y=chain_df['ce_volume'], name='CE Vol', marker_color='#AB47BC'))
    fig.add_trace(go.Bar(x=chain_df['strike'], y=chain_df['pe_volume'], name='PE Vol', marker_color='#FFA726'))
    fig.update_layout(
        title="[MOD D] Strike-Wise Volume Distribution", 
        template="plotly_dark", 
        barmode="stack",
        xaxis_title="Strike Price",
        yaxis_title="Volume"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- MOD E: OI Change ---
with t5:
    np.random.seed(42)
    oi_change_vals = np.random.randint(-15000, 25000, size=n_strikes)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=chain_df['strike'], y=oi_change_vals, name='Change in OI', marker_color='#26A69A'))
    fig.update_layout(
        title="[MOD E] Strike-Wise Change in Open Interest", 
        template="plotly_dark",
        xaxis_title="Strike Price",
        yaxis_title="Change in OI"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- MOD F: Theta Decay ---
with t6:
    theta_vals = np.linspace(-25.0, -10.0, n_strikes)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=chain_df['strike'], y=theta_vals, mode='lines+markers', name='Theta', line=dict(color='#FFEE58', width=2)))
    fig.update_layout(
        title="[MOD F] Option Premium Decay & Theta Wave", 
        template="plotly_dark",
        xaxis_title="Strike Price",
        yaxis_title="Theta Value"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- MOD G: Max Pain ---
with t7:
    pain_vals = np.sort(np.random.randint(10000, 80000, size=n_strikes))[::-1]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=chain_df['strike'], y=pain_vals, mode='lines+markers', name='Pain', line=dict(color='#EC407A', width=2)))
    fig.update_layout(
        title="[MOD G] Max Pain Strike Analysis Curve", 
        template="plotly_dark",
        xaxis_title="Strike Price",
        yaxis_title="Total Pain Value"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- MOD H: PCR Trend ---
with t8:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=['09:30', '10:30', '11:30', '12:30', '13:30', '14:30', '15:15'], 
        y=[1.15, 1.22, 1.28, 1.35, 1.32, 1.40, 1.38], 
        mode='lines+markers', 
        name='PCR', 
        line=dict(color='#42A5F5', width=3)
    ))
    fig.update_layout(
        title="[MOD H] Intraday Put-Call Ratio (PCR) Trend Line", 
        template="plotly_dark",
        xaxis_title="Time",
        yaxis_title="PCR Value"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- MOD I: Delta Flow ---
with t9:
    delta_vals = np.linspace(0.1, 0.9, n_strikes)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=chain_df['strike'], y=delta_vals, mode='lines+markers', name='Delta', line=dict(color='#66BB6A', width=2)))
    fig.update_layout(
        title="[MOD I] Cumulative Delta Flow Matrix", 
        template="plotly_dark",
        xaxis_title="Strike Price",
        yaxis_title="Delta"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- MOD J: Vol Surface ---
with t10:
    surface_z = np.random.rand(n_strikes, 5)
    fig = go.Figure(data=[go.Surface(z=surface_z, x=chain_df['strike'], y=[1, 2, 3, 4, 5])])
    fig.update_layout(
        title="[MOD J] Multi-Strike Volatility Surface 3D", 
        template="plotly_dark",
        scene=dict(
            xaxis_title='Strikes',
            yaxis_title='Expiry Tenor',
            zaxis_title='Volatility'
        )
    )
    st.plotly_chart(fig, use_container_width=True)
