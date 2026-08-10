import streamlit as st
from database import init_db
from dhan_api import verify_dhan_credentials
from dhan_websocket import DhanWebSocket

# डेटाबेस इनिशियलाइज़ करें
init_db()

# पेज का लेआउट सेट करें
st.set_page_config(
    page_title="Dhan Institutional Trading Platform", 
    page_icon="📊", 
    layout="wide"
)

# 1. सेशन स्टेट इनिशियलाइज़ेशन (सारे वेरिएबल्स एक जगह सुरक्षित)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "client_id" not in st.session_state:
    st.session_state.client_id = ""
if "access_token" not in st.session_state:
    st.session_state.access_token = ""

# =====================================================================
# 📌 SIDEBAR LOGIN & AUTHENTICATION
# =====================================================================
st.sidebar.title("📊 Dhan Platform")

if not st.session_state.logged_in:
    st.sidebar.subheader("🔑 Login to Dhan")
    with st.sidebar.form("login_form"):
        # सेशन स्टेट से वैल्यूज को इनपुट फील्ड में होल्ड रखना ताकि री-रन पर उड़े नहीं
        cid = st.text_input("Client ID", value=st.session_state.client_id)
        token = st.text_input("Access Token", type="password", value=st.session_state.access_token)
        
        submitted = st.form_submit_button("Login")
        if submitted:
            if cid and token:
                valid, msg = verify_dhan_credentials(cid, token)
                if valid:
                    st.session_state.logged_in = True
                    st.session_state.client_id = cid
                    st.session_state.access_token = token
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("Please enter both Client ID and Access Token.")
else:
    st.sidebar.success(f"Connected (ID: {st.session_state.client_id})")
    
    # लाइव वेबसॉकेट बैकग्राउंड में शुरू करना
    if "ws_client" not in st.session_state:
        try:
            st.session_state.ws_client = DhanWebSocket(st.session_state.client_id, st.session_state.access_token)
            st.session_state.ws_client.start()
        except Exception as e:
            st.sidebar.warning(f"WebSocket Warning: {e}")

    st.sidebar.markdown("---")
    st.sidebar.info("👉 नीचे दिए गए पेजों पर क्लिक करके नेविगेट करें:")
    
    if st.sidebar.button("Logout", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.client_id = ""
        st.session_state.access_token = ""
        if "ws_client" in st.session_state:
            del st.session_state.ws_client
        st.rerun()

# =====================================================================
# 📌 MAIN HOME SCREEN (जब यूजर लॉग इन न हो)
# =====================================================================
if not st.session_state.logged_in:
    st.title("🚀 Welcome to Dhan Custom Institutional Trading App")
    st.write("शुरू करने के लिए कृपया अपने **Client ID** और **Access Token** के साथ साइडबार में लॉगिन करें।")
    
    st.markdown("---")
    st.markdown("### 🌟 Platform Features:")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("📊 **Option Chain & Analytics**\n- PCR, Max Pain & Net GEX\n- Auto-fetched Expiry & Lot Sizes")
    with col2:
        st.info("📈 **Advanced Charts**\n- Historical Data & RSI\n- SMA, EMA & Risk Management")
    with col3:
        st.info("💼 **Portfolio & Journal**\n- Live Holdings & Positions\n- SQLite Trading Journal")

else:
    # जब यूजर सक्सेसफुली लॉगिन हो जाए
    st.title("🎯 Dhan Trading Dashboard")
    st.success("आप सफलतापूर्वक कनेक्ट हो चुके हैं! अब आप साइडबार से किसी भी पेज (Option Chain, Charts, Portfolio आदि) का चयन कर सकते हैं।")
    
    # क्विक ओवरव्यू कार्ड्स
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric(label="Active Client ID", value=st.session_state.client_id)
    with m2:
        st.metric(label="Connection Status", value="Connected 🟢")
    with m3:
        st.metric(label="WebSocket Feed", value="Active ⚡")
