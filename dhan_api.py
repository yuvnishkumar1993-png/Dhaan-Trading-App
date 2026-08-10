import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

class InstitutionalDataEngine:
    """
    Quant Terminal Pro के लिए Advanced Data Pipeline और Caching Engine.
    Dhan API से लाइव ऑप्शन चैन, एक्सपायरी और ग्रीक्स फेच करने का वेरीफाइड इंजन।
    """
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def load_scrip_master():
        """Dhan Cloud से universal scrip master database download करता है।"""
        try:
            url = "https://images.dhan.co/api-data/api-scrip-master.csv"
            df = pd.read_csv(url, low_memory=False)
            df.columns = [str(col).strip().upper() for col in df.columns]
            return df
        except Exception as e:
            st.error(f"Scrip Master Download Error: {e}")
            return pd.DataFrame()

    @staticmethod
    @st.cache_data(ttl=60)
    def fetch_expiries(client_id, access_token, sec_id, seg):
        """Selected underlying के लिए active expiry dates की list लाता है।"""
        if not client_id or not access_token:
            return [datetime.now().strftime("%Y-%m-%d")]
            
        url = "https://api.dhan.co/v2/optionchain/expirylist"
        headers = {
            "access-token": access_token.strip(), 
            "client-id": client_id.strip(), 
            "Content-Type": "application/json"
        }
        payload = {"UnderlyingScrip": int(sec_id), "UnderlyingSeg": str(seg).strip()}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=8)
            if response.status_code == 200:
                res = response.json()
                if res.get("status") == "success":
                    return res.get("data", [])
        except Exception:
            pass
        return [datetime.now().strftime("%Y-%m-%d")]

    @staticmethod
    @st.cache_data(ttl=10)
    def fetch_live_option_chain(client_id, access_token, sec_id, seg, exp, symbol):
        """Real-time option chain data fetch करता है। यदि क्रेडेंशियल्स न हों तो खाली डेटा लौटाता है (फर्जी डेटा नहीं)।"""
        if not client_id or not access_token:
            return pd.DataFrame(), 0.0

        url = "https://api.dhan.co/v2/optionchain"
        headers = {
            "access-token": access_token.strip(), 
            "client-id": client_id.strip(), 
            "Content-Type": "application/json"
        }
        payload = {
            "UnderlyingScrip": int(sec_id), 
            "UnderlyingSeg": str(seg).strip(), 
            "Expiry": str(exp).strip()
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                res = response.json()
                block = res.get("data", {})
                spot_val = float(block.get("last_price", 0.0))
                oc_map = block.get("oc", {})
                
                if oc_map:
                    records = []
                    for s_str, obj in oc_map.items():
                        s_val = float(s_str)
                        ce, pe = obj.get("ce", {}), obj.get("pe", {})
                        
                        ce_oi = int(ce.get("oi", 0))
                        pe_oi = int(pe.get("oi", 0))
                        
                        records.append({
                            "Strike": int(s_val),
                            "Call_OI": ce_oi,
                            "Call_Chg_OI": ce_oi - int(ce.get("previous_oi", 0)),
                            "Call_Volume": int(ce.get("volume", 0)),
                            "Call_IV": float(ce.get("iv", 16.0)),
                            "Call_LTP": float(ce.get("last_price", 0.0)),
                            "Call_Delta": float(ce.get("delta", 0.50)),
                            "Call_Gamma": float(ce.get("gamma", 0.0018)),
                            "Put_LTP": float(pe.get("last_price", 0.0)),
                            "Put_IV": float(pe.get("iv", 16.0)),
                            "Put_Volume": int(pe.get("volume", 0)),
                            "Put_Chg_OI": pe_oi - int(pe.get("previous_oi", 0)),
                            "Put_OI": pe_oi,
                            "Put_Delta": float(pe.get("delta", -0.50)),
                            "Put_Gamma": float(pe.get("gamma", 0.0018))
                        })
                    df_out = pd.DataFrame(records)
                    if not df_out.empty:
                        df_out = df_out.sort_values(by="Strike").reset_index(drop=True)
                    return df_out, spot_val
        except Exception as e:
            st.error(f"API Connection Error: {e}")
            
        return pd.DataFrame(), 0.0

def verify_dhan_credentials(client_id, access_token):
    url = "https://api.dhan.co/v2/holdings"
    headers = {"access-token": access_token.strip(), "client-id": client_id.strip(), "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True, "Success"
        elif response.status_code == 401:
            return False, "Token Expired or Invalid"
        return False, f"API Error {response.status_code}"
    except Exception as e:
        return False, f"Connection Failed: {str(e)}"
