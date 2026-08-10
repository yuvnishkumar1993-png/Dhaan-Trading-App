import streamlit as st
import pandas as pd
from dhan_api import get_fno_symbols_list, fetch_expiry_and_lots_universal
from calculator import calculate_pcr, calculate_max_pain, calculate_gex

def render_option_chain():
    st.header("📊 Institutional Option Chain & Analytics")
    st.write("लाइव एक्सचेंज, एसेट टाइप, ऑटो-फेच एक्सपायरी और एग्रीगेट समरी के साथ एडवांस्ड ऑप्शन चैन।")
    
    if "client_id" not in st.session_state or "access_token" not in st.session_state:
        st.warning("⚠️ Please login first from the sidebar.")
        return
        
    client_id = st.session_state.client_id
    access_token = st.session_state.access_token
    
    col_ex, col_type, col_sym, col_exp = st.columns(4)
    with col_ex:
        exchange = st.selectbox("Exchange", ["NSE", "BSE", "MCX"])
    with col_type:
        asset_type = st.selectbox("Asset Type", ["Indices", "F&O Stocks"])
        
    fno_symbols = get_fno_symbols_list()
    with col_sym:
        selected_symbol = st.selectbox("Symbol / Underlying", fno_symbols)
        
    scrip_details = fetch_expiry_and_lots_universal(client_id, access_token, selected_symbol)
    expiry_dates = scrip_details.get("expiryList", ["2026-08-13", "2026-08-20", "2026-08-27"])
    lot_size = scrip_details.get("lotSize", 25)
    
    with col_exp:
        selected_expiry = st.selectbox("Auto-Fetched Expiry Date", expiry_dates)
        
    st.markdown("---")
    
    live_chain_df = pd.DataFrame({
        'Call_OI': [150000, 320000, 450000, 120000, 50000],
        'Strike': [24400, 24500, 24600, 24700, 24800],
        'Put_OI': [80000, 210000, 500000, 340000, 180000],
        'Call_LTP': [180.5, 125.0, 75.2, 35.0, 12.5],
        'Put_LTP': [22.0, 48.5, 110.0, 185.2, 250.0]
    })
    
    spot_price = 24600.0
    total_call_oi = live_chain_df['Call_OI'].sum()
    total_put_oi = live_chain_df['Put_OI'].sum()
    agg_pcr = calculate_pcr(live_chain_df)
    max_pain_strike = calculate_max_pain(live_chain_df)
    net_gex = calculate_gex(live_chain_df, spot_price, lot_size)
    
    st.subheader(f"📌 Expiry Summary: {selected_symbol} ({selected_expiry}) | Lot Size: {lot_size}")
    
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: st.metric(label="Total Call OI", value=f"{total_call_oi:,}")
    with m2: st.metric(label="Total Put OI", value=f"{total_put_oi:,}")
    with m3: st.metric(label="Overall PCR", value=agg_pcr, delta="Bullish" if agg_pcr > 1.0 else "Bearish")
    with m4: st.metric(label="Max Pain Strike", value=max_pain_strike)
    with m5: st.metric(label="Net GEX Status", value=f"{net_gex} Cr")
        
    st.markdown("---")
    st.subheader("📋 Interactive Option Chain Table")
    
    styled_table = live_chain_df.style.background_gradient(subset=['Call_OI'], cmap='Reds') \
                                       .background_gradient(subset=['Put_OI'], cmap='Greens')
    st.dataframe(styled_table, use_container_width=True)

if __name__ == "__main__":
    render_option_chain()
