import requests
import streamlit as st
import logging

def verify_dhan_credentials(client_id, access_token):
    """Dhan API के जरिए Client ID और Access Token को लाइव वेरीफाई करना"""
    url = "https://api.dhan.co/v2/holdings"
    headers = {
        "access-token": access_token, 
        "client-id": client_id, 
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True, "Success"
        elif response.status_code == 401:
            return False, "Token Expired or Invalid Client ID/Token"
        elif response.status_code == 404:
            return False, "API Endpoint Not Found (404)"
        return False, f"API Error {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Connection Failed: {str(e)}"

@st.cache_data(ttl=600)
def fetch_historical_data(client_id, access_token, security_id, exchange_segment):
    """लाइव हिस्टोरिकल चार्ट डेटा फेच करना"""
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

def fetch_live_option_chain(client_id, access_token, underlying_scrip, underlying_seg):
    """सीधे Dhan API से लाइव ऑप्शन चैन डेटा फेच करना"""
    url = "https://api.dhan.co/v2/optionchain"
    headers = {
        "access-token": access_token, 
        "client-id": client_id, 
        "Content-Type": "application/json"
    }
    payload = {
        "underlyingScrip": int(underlying_scrip),
        "underlyingSeg": underlying_seg
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {"error": "Token Expired"}
        return {"error": f"API Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Connection Failed: {str(e)}"}

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
