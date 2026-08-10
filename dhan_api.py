import requests
import streamlit as st
import logging

FNO_MASTER_DATA = {
    "NIFTY": {"securityId": 13, "segment": "IDX_I", "lotSize": 25},
    "BANKNIFTY": {"securityId": 25, "segment": "IDX_I", "lotSize": 15},
    "FINNIFTY": {"securityId": 27, "segment": "IDX_I", "lotSize": 25},
    "MIDCPNIFTY": {"securityId": 28, "segment": "IDX_I", "lotSize": 50},
    "SENSEX": {"securityId": 1, "segment": "BSE_IDX", "lotSize": 10},
    "RELIANCE": {"securityId": 2885, "segment": "NSE_EQ", "lotSize": 250},
    "TCS": {"securityId": 11536, "segment": "NSE_EQ", "lotSize": 175},
    "INFY": {"securityId": 1594, "segment": "NSE_EQ", "lotSize": 400},
    "HDFCBANK": {"securityId": 1333, "segment": "NSE_EQ", "lotSize": 550},
    "ICICIBANK": {"securityId": 4963, "segment": "NSE_EQ", "lotSize": 700}
}

def get_fno_symbols_list():
    return list(FNO_MASTER_DATA.keys())

def verify_dhan_credentials(client_id, access_token):
    url = "https://api.dhan.co/v2/holdings"
    headers = {"access-token": access_token, "client-id": client_id, "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True, "Success"
        elif response.status_code == 401:
            return False, "Token Expired or Invalid"
        elif response.status_code == 404:
            return False, "API Endpoint Not Found (404)"
        return False, f"API Error {response.status_code}"
    except Exception as e:
        return False, f"Connection Failed: {str(e)}"

@st.cache_data(ttl=600)
def fetch_historical_data(client_id, access_token, security_id, exchange_segment):
    url = "https://api.dhan.co/v2/charts/historical"
    headers = {"access-token": access_token, "client-id": client_id, "Content-Type": "application/json"}
    payload = {"securityId": security_id, "exchangeSegment": exchange_segment, "instrument": "EQUITY", "expiryCode": 0}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {"error": "Token Expired", "message": "Please re-login."}
        return {"error": f"API Error: {response.status_code}", "message": response.text}
    except Exception as e:
        logging.error(f"Historical Data Error: {str(e)}")
        return {"error": "Connection Failed", "message": str(e)}

def fetch_expiry_and_lots_universal(client_id, access_token, symbol_name):
    scrip_info = FNO_MASTER_DATA.get(symbol_name, {"securityId": 13, "segment": "IDX_I", "lotSize": 25})
    return {
        "securityId": scrip_info["securityId"],
        "lotSize": scrip_info["lotSize"],
        "expiryList": ["2026-08-13", "2026-08-20", "2026-08-27", "2026-09-24"]
    }

def fetch_holdings(client_id, access_token):
    url = "https://api.dhan.co/v2/holdings"
    headers = {"access-token": access_token, "client-id": client_id, "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {"error": "Token Expired"}
        return {"error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def fetch_positions(client_id, access_token):
    url = "https://api.dhan.co/v2/positions"
    headers = {"access-token": access_token, "client-id": client_id, "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {"error": "Token Expired"}
        return {"error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}
