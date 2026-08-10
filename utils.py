import math
import pandas as pd
import numpy as np

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
            if exp_price > K:
                payout += (exp_price - K) * ce_oi[i]
            if exp_price < K:
                payout += (K - exp_price) * pe_oi[i]
        if payout < min_payout:
            min_payout = payout
            max_pain_strike = exp_price
    return int(max_pain_strike)

def calculate_advanced_metrics(df, spot, lot):
    if df is None or df.empty or 'Strike' not in df.columns:
        return df
        
    r, T = 0.06, 2 / 365.0
    ce_deltas, pe_deltas, gammas, ce_thetas, vegas = [], [], [], [], []
    ce_vannas, ce_charms, ce_gexs, pe_gexs, ce_turnovers, pe_turnovers = [], [], [], [], [], []
    
    for _, row in df.iterrows():
        K = row['Strike']
        call_oi = row.get('Raw_CE_OI', 100000)
        put_oi = row.get('Raw_PE_OI', 100000)
        c_ltp, p_ltp = row.get('CE_LTP', 10.0), row.get('PE_LTP', 10.0)
        c_vol = row.get('CE_Volume', row.get('Call_Volume', 100000))
        p_vol = row.get('PE_Volume', row.get('Put_Volume', 100000))
        c_iv = max(5.0, row.get('CE_IV', row.get('Call_IV', 13.0))) / 100.0
        p_iv = max(5.0, row.get('PE_IV', row.get('Put_IV', 13.5))) / 100.0
        sigma = (c_iv + p_iv) / 2.0
        
        try:
            d1 = (math.log(spot / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            cdf_d1, pdf_d1 = norm_cdf(d1), norm_pdf(d1)
            
            c_delta = round(cdf_d1, 2)
            p_delta = round(cdf_d1 - 1.0, 2)
            gamma = round(pdf_d1 / (spot * sigma * math.sqrt(T)), 5)
            c_theta = round((- (spot * pdf_d1 * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm_cdf(d2)) / 365.0, 2)
            p_theta = round((- (spot * pdf_d1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365.0, 2)
            vega = round((spot * math.sqrt(T) * pdf_d1) / 100.0, 2)
            vanna = round(-pdf_d1 * d2 / sigma, 4)
            charm = round(-pdf_d1 * (2 * r * T - d2 * sigma * math.sqrt(T)) / (2 * T * sigma * math.sqrt(T)) / 365.0, 4)
        except Exception:
            c_delta, p_delta, gamma, c_theta, p_theta, vega, vanna, charm = 0.5, -0.5, 0.001, -5.0, -5.0, 10.0, 0.01, -0.01

        ce_gex = round(call_oi * lot * (spot ** 2) * gamma / 100000000.0, 2)
        pe_gex = round(put_oi * lot * (spot ** 2) * gamma / 100000000.0, 2)
        c_turnover = round((c_vol * c_ltp * lot) / 10000000.0, 2)
        p_turnover = round((p_vol * p_ltp * lot) / 10000000.0, 2)

        ce_deltas.append(c_delta); pe_deltas.append(p_delta); gammas.append(gamma)
        ce_thetas.append(c_theta); pe_thetas.append(p_theta); vegas.append(vega)
        ce_vannas.append(vanna); ce_charms.append(charm)
        ce_gexs.append(ce_gex); pe_gexs.append(pe_gex)
        ce_turnovers.append(c_turnover); pe_turnovers.append(p_turnover)
        
    df['CE Delta'] = ce_deltas; df['PE Delta'] = pe_deltas; df['Gamma'] = gammas
    df['CE Theta'] = ce_thetas; df['PE Theta'] = pe_thetas; df['CE Vega'] = vegas; df['PE Vega'] = vegas
    df['CE Vanna'] = ce_vannas; df['PE Vanna'] = ce_vannas
    df['CE Charm'] = ce_charms; df['PE Charm'] = ce_charms
    df['CE GEX (Cr)'] = ce_gexs; df['PE GEX (Cr)'] = pe_gexs
    df['CE Turnover (Cr)'] = ce_turnovers; df['PE Turnover (Cr)'] = pe_turnovers
    return df

def get_buildup(chg_oi, pct_chg):
    if pct_chg > 0 and chg_oi > 0: return "Short Build"
    elif pct_chg < 0 and chg_oi < 0: return "Long Unwind"
    elif pct_chg > 0 and chg_oi < 0: return "Short Cover"
    return "Long Build"
