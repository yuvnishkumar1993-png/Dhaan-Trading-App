import math
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def norm_cdf(x): 
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x): 
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

def fetch_available_expiries(client_id, access_token, sec_id, seg):
    """
    असली Dhan API से एक्सपायरी डेट्स फेच करता है। 
    यदि API उपलब्ध नहीं है, तो आने वाले गुरुवार (Thursdays) की लिस्ट ऑटोमैटिकली जनरेट कर देता है।
    """
    try:
        from dhan_api import InstitutionalDataEngine
        expiries = InstitutionalDataEngine.fetch_expiries(client_id, access_token, sec_id, seg)
        if expiries:
            return expiries
    except Exception:
        pass
    
    # फॉलबैक: आगामी 4-5 गुरुवार (Thursdays) की डमी/ऑटोमैटिक एक्सपायरी डेट्स
    expiries = []
    today = datetime.now()
    # अगले गुरुवार का पता लगाना
    days_ahead = (3 - today.weekday() + 7) % 7  # 3 means Thursday
    if days_ahead == 0:
        days_ahead = 7
    next_thursday = today + timedelta(days=days_ahead)
    
    for i in range(4):
        exp_date = next_thursday + timedelta(weeks=i)
        expiries.append(exp_date.strftime("%Y-%m-%d"))
        
    return expiries

def fetch_market_option_chain(client_id, access_token, sec_id, seg, expiry, symbol):
    """असली Dhan API या फॉलबैक से ऑप्शन चेन डेटा फेच करता है"""
    try:
        from dhan_api import InstitutionalDataEngine
        df, spot = InstitutionalDataEngine.fetch_live_option_chain(
            client_id, access_token, sec_id, seg, expiry, symbol
        )
        if df is not None and not df.empty:
            return normalize_columns(df), spot
    except Exception:
        pass
    
    # फॉलबैक डायनेमिक सिमुलेशन
    spot = 24583.80
    strikes = np.arange(spot - 1000, spot + 1000, 50)
    recs = []
    for st_val in strikes:
        recs.append({
            "Strike": int(st_val),
            "STRIKE": int(st_val),
            "Raw_CE_OI": np.random.randint(500000, 2000000),
            "Raw_PE_OI": np.random.randint(500000, 2000000),
            "CE_Chg_OI": np.random.randint(-20000, 50000),
            "PE_Chg_OI": np.random.randint(-20000, 50000),
            "CE_Volume": 1000000, "PE_Volume": 1000000,
            "CE_IV": 13.0, "PE_IV": 13.5,
            "CE_LTP": max(1.0, spot - st_val + 20),
            "PE_LTP": max(1.0, st_val - spot + 20)
        })
    return pd.DataFrame(recs), spot

def normalize_columns(df):
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Strike', 'STRIKE', 'strike_price', 'StrikePrice']:
        if col in df.columns:
            df['Strike'] = pd.to_numeric(df[col], errors='coerce')
            break
    if 'Strike' not in df.columns:
        df['Strike'] = pd.to_numeric(df.iloc[:, 0], errors='coerce')
        
    df.dropna(subset=['Strike'], inplace=True)
    df['STRIKE'] = df['Strike']

    if 'Raw_CE_OI' not in df.columns:
        for c in ['CE_OI', 'Call_OI', 'CE_OpenInterest']:
            if c in df.columns:
                df['Raw_CE_OI'] = pd.to_numeric(df[c], errors='coerce').fillna(100000)
                break
        if 'Raw_CE_OI' not in df.columns:
            df['Raw_CE_OI'] = 100000

    if 'Raw_PE_OI' not in df.columns:
        for c in ['PE_OI', 'Put_OI', 'PE_OpenInterest']:
            if c in df.columns:
                df['Raw_PE_OI'] = pd.to_numeric(df[c], errors='coerce').fillna(100000)
                break
        if 'Raw_PE_OI' not in df.columns:
            df['Raw_PE_OI'] = 100000

    return df

def calculate_max_pain(df, spot=0):
    if df is None or df.empty:
        return int(spot) if spot else 0
        
    strikes = df['Strike'].values
    ce_oi = df['Raw_CE_OI'].values
    pe_oi = df['Raw_PE_OI'].values
    
    min_payout = float('inf')
    max_pain_strike = strikes[0]
    
    for exp_price in strikes:
        call_pain = np.maximum(0, exp_price - strikes) * ce_oi
        put_pain = np.maximum(0, strikes - exp_price) * pe_oi
        total_pain = (call_pain + put_pain).sum()
        
        if total_pain < min_payout:
            min_payout = total_pain
            max_pain_strike = exp_price
            
    return int(max_pain_strike)

def calculate_advanced_metrics(df, spot, lot):
    if df is None or df.empty or 'Strike' not in df.columns: 
        return df
        
    r, T = 0.06, 2 / 365.0
    res = {k: [] for k in ['CE Delta', 'PE Delta', 'Gamma', 'CE Vega', 'PE Vega', 'CE GEX (Cr)', 'PE GEX (Cr)']}
    
    for _, row in df.iterrows():
        K = float(row.get('Strike', spot))
        c_iv = max(5.0, float(row.get('CE_IV', 13.0))) / 100.0
        p_iv = max(5.0, float(row.get('PE_IV', 13.5))) / 100.0
        sigma = (c_iv + p_iv) / 2.0
        
        cd, pd_val, gam, veg = 0.5, -0.5, 0.001, 10.0
        try:
            if spot > 0 and K > 0 and sigma > 0 and T > 0:
                d1 = (math.log(spot / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
                cdf_d1, pdf_d1 = norm_cdf(d1), norm_pdf(d1)
                cd = round(cdf_d1, 2)
                pd_val = round(cdf_d1 - 1.0, 2)
                gam = round(pdf_d1 / (spot * sigma * math.sqrt(T)), 5)
                veg = round((spot * math.sqrt(T) * pdf_d1) / 100.0, 2)
        except Exception:
            pass

        res['CE Delta'].append(cd)
        res['PE Delta'].append(pd_val)
        res['Gamma'].append(gam)
        res['CE Vega'].append(veg)
        res['PE Vega'].append(veg)
        
        raw_ce_oi = float(row.get('Raw_CE_OI', 0) or 0)
        raw_pe_oi = float(row.get('Raw_PE_OI', 0) or 0)
        res['CE GEX (Cr)'].append(round(raw_ce_oi * lot * (spot**2) * gam / 10**8, 2))
        res['PE GEX (Cr)'].append(round(raw_pe_oi * lot * (spot**2) * gam / 10**8, 2))

    for col_name, val_list in res.items():
        df[col_name] = val_list
        
    return df
