import math
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
    
    ce_deltas, pe_deltas, gammas = [], [], []
    ce_thetas, pe_thetas, vegas = [], [], []
    ce_vannas, pe_vannas = [], []
    ce_charms, pe_charms = [], []
    ce_gexs, pe_gexs = [], []
    ce_turnovers, pe_turnovers = [], []
    
    for _, row in df.iterrows():
        K = float(row.get('Strike', spot))
        c_iv = max(5.0, float(row.get('CE_IV', 13.0))) / 100.0
        p_iv = max(5.0, float(row.get('PE_IV', 13.5))) / 100.0
        sigma = (c_iv + p_iv) / 2.0
        
        # Default fallback values defined BEFORE try-except to prevent NameError
        c_delta, p_delta = 0.5, -0.5
        gamma = 0.001
        c_theta, p_theta = -5.0, -5.0
        vega = 10.0
        vanna = 0.01
        charm = -0.01
        
        try:
            if spot > 0 and K > 0 and sigma > 0 and T > 0:
                d1 = (math.log(spot / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
                d2 = d1 - sigma * math.sqrt(T)
                cdf_d1, pdf_d1 = norm_cdf(d1), norm_pdf(d1)
                
                c_delta = round(cdf_d1, 2)
                p_delta = round(cdf_d1 - 1.0, 2)
                gamma = round(pdf_d1 / (spot * sigma * math.sqrt(T)), 5)
                c_theta = round((-(spot * pdf_d1 * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm_cdf(d2)) / 365.0, 2)
                p_theta = round((-(spot * pdf_d1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365.0, 2)
                vega = round((spot * math.sqrt(T) * pdf_d1) / 100.0, 2)
                vanna = round(-pdf_d1 * d2 / sigma, 4)
                charm = round(-pdf_d1 * (2 * r * T - d2 * sigma * math.sqrt(T)) / (2 * T * sigma * math.sqrt(T)) / 365.0, 4)
        except Exception:
            pass

        ce_deltas.append(c_delta)
        pe_deltas.append(p_delta)
        gammas.append(gamma)
        ce_thetas.append(c_theta)
        pe_thetas.append(p_theta)
        vegas.append(vega)
        ce_vannas.append(vanna)
        pe_vannas.append(vanna)
        ce_charms.append(charm)
        pe_charms.append(charm)
        
        raw_ce_oi = float(row.get('Raw_CE_OI', 0) or 0)
        raw_pe_oi = float(row.get('Raw_PE_OI', 0) or 0)
        ce_vol = float(row.get('CE_Volume', 0) or 0)
        pe_vol = float(row.get('PE_Volume', 0) or 0)
        ce_ltp = float(row.get('CE_LTP', 0) or 0)
        pe_ltp = float(row.get('PE_LTP', 0) or 0)
        
        ce_gexs.append(round(raw_ce_oi * lot * (spot**2) * gamma / 10**8, 2))
        pe_gexs.append(round(raw_pe_oi * lot * (spot**2) * gamma / 10**8, 2))
        ce_turnovers.append(round((ce_vol * ce_ltp * lot) / 10**7, 2))
        pe_turnovers.append(round((pe_vol * pe_ltp * lot) / 10**7, 2))

    df['CE Delta'] = ce_deltas
    df['PE Delta'] = pe_deltas
    df['Gamma'] = gammas
    df['CE Theta'] = ce_thetas
    df['PE Theta'] = pe_thetas
    df['CE Vega'] = vegas
    df['PE Vega'] = vegas
    df['CE Vanna'] = ce_vannas
    df['PE Vanna'] = pe_vannas
    df['CE Charm'] = ce_charms
    df['PE Charm'] = ce_charms
    df['CE GEX (Cr)'] = ce_gexs
    df['PE GEX (Cr)'] = pe_gexs
    df['CE Turnover (Cr)'] = ce_turnovers
    df['PE Turnover (Cr)'] = pe_turnovers
    return df

def get_buildup(chg_oi, pct_chg):
    if pct_chg > 0 and chg_oi > 0: 
        return "Short Build"
    elif pct_chg < 0 and chg_oi < 0: 
        return "Long Unwind"
    elif pct_chg > 0 and chg_oi < 0: 
        return "Short Cover"
    return "Long Build"
