import math
import numpy as np
import pandas as pd

def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x):
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

def calculate_max_pain(df, spot):
    if df is None or df.empty or 'Strike' not in df.columns:
        return int(spot)
    strikes = df['Strike'].values
    ce_oi = df['Raw_CE_OI'].values
    pe_oi = df['Raw_PE_OI'].values
    min_payout = float('inf')
    max_pain_strike = strikes[0]
    
    for exp_price in strikes:
        payout = 0
        for i, K in enumerate(strikes):
            if exp_price > K: payout += (exp_price - K) * ce_oi[i]
            if exp_price < K: payout += (K - exp_price) * pe_oi[i]
        if payout < min_payout:
            min_payout = payout
            max_pain_strike = exp_price
    return int(max_pain_strike)

def calculate_advanced_metrics(df, spot, lot):
    if df is None or df.empty or 'Strike' not in df.columns:
        return df
        
    r, T = 0.06, 2 / 365.0
    cols = ['CE Delta', 'PE Delta', 'Gamma', 'CE Theta', 'PE Theta', 'CE Vega', 
            'CE Vanna', 'CE Charm', 'CE GEX (Cr)', 'PE GEX (Cr)', 'CE Turnover (Cr)', 'PE Turnover (Cr)']
    
    data_map = {c: [] for c in cols}
    
    for _, row in df.iterrows():
        K = row.get('Strike', spot)
        c_iv = max(5.0, float(row.get('CE_IV', 13.0))) / 100.0
        p_iv = max(5.0, float(row.get('PE_IV', 13.5))) / 100.0
        sigma = (c_iv + p_iv) / 2.0
        
        try:
            d1 = (math.log(spot / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            cdf_d1, pdf_d1 = norm_cdf(d1), norm_pdf(d1)
            
            # Greeks Calculation
            c_delta, p_delta = round(cdf_d1, 2), round(cdf_d1 - 1.0, 2)
            gamma = round(pdf_d1 / (spot * sigma * math.sqrt(T)), 5)
            c_theta = round((-(spot * pdf_d1 * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm_cdf(d2)) / 365.0, 2)
            p_theta = round((-(spot * pdf_d1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365.0, 2)
            vega = round((spot * math.sqrt(T) * pdf_d1) / 100.0, 2)
            vanna = round(-pdf_d1 * d2 / sigma, 4)
            charm = round(-pdf_d1 * (2 * r * T - d2 * sigma * math.sqrt(T)) / (2 * T * sigma * math.sqrt(T)) / 365.0, 4)
        except:
            c_delta, p_delta, gamma, c_theta, p_theta, vega, vanna, charm = 0.5, -0.5, 0.001, -5.0, -5.0, 10.0, 0.01, -0.01

        data_map['CE Delta'].append(c_delta); data_map['PE Delta'].append(p_delta)
        data_map['Gamma'].append(gamma); data_map['CE Theta'].append(c_theta)
        data_map['PE Theta'].append(p_theta); data_map['CE Vega'].append(vega)
        data_map['CE Vanna'].append(vanna); data_map['CE Charm'].append(charm)
        
        # GEX and Turnover
        ce_gex = round(row.get('Raw_CE_OI', 0) * lot * (spot**2) * gamma / 10**8, 2)
        pe_gex = round(row.get('Raw_PE_OI', 0) * lot * (spot**2) * gamma / 10**8, 2)
        data_map['CE GEX (Cr)'].append(ce_gex); data_map['PE GEX (Cr)'].append(pe_gex)
        data_map['CE Turnover (Cr)'].append(round((row.get('CE_Volume', 0) * row.get('CE_LTP', 0) * lot) / 10**7, 2))
        data_map['PE Turnover (Cr)'].append(round((row.get('PE_Volume', 0) * row.get('PE_LTP', 0) * lot) / 10**7, 2))

    for col, values in data_map.items(): df[col] = values
    df['PE Vega'] = df['CE Vega']; df['PE Vanna'] = df['CE Vanna']; df['PE Charm'] = df['CE Charm']
    return df

def get_buildup(chg_oi, pct_chg):
    if pct_chg > 0 and chg_oi > 0: return "Short Build"
    elif pct_chg < 0 and chg_oi < 0: return "Long Unwind"
    elif pct_chg > 0 and chg_oi < 0: return "Short Cover"
    return "Long Build"
