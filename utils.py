import math
import numpy as np
import pandas as pd

def norm_cdf(x): return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
def norm_pdf(x): return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

def calculate_max_pain(df, spot):
    if df is None or df.empty or 'Strike' not in df.columns: return int(spot)
    strikes, ce_oi, pe_oi = df['Strike'].values, df['Raw_CE_OI'].values, df['Raw_PE_OI'].values
    min_payout, max_pain_strike = float('inf'), strikes[0]
    for exp_price in strikes:
        payout = sum((exp_price - K) * ce_oi[i] if exp_price > K else (K - exp_price) * pe_oi[i] for i, K in enumerate(strikes))
        if payout < min_payout: min_payout, max_pain_strike = payout, exp_price
    return int(max_pain_strike)

def calculate_advanced_metrics(df, spot, lot):
    if df is None or df.empty or 'Strike' not in df.columns: return df
    
    # ग्रीक्स के लिए लिस्ट तैयार करें
    results = {
        'CE Delta': [], 'PE Delta': [], 'Gamma': [], 'CE Theta': [], 'PE Theta': [],
        'CE Vega': [], 'PE Vega': [], 'CE Vanna': [], 'PE Vanna': [], 'CE Charm': [], 
        'PE Charm': [], 'CE GEX (Cr)': [], 'PE GEX (Cr)': [], 'CE Turnover (Cr)': [], 'PE Turnover (Cr)': []
    }

    r, T = 0.06, 2 / 365.0
    for _, row in df.iterrows():
        K = row.get('Strike', spot)
        c_iv = max(5.0, float(row.get('CE_IV', 13.0))) / 100.0
        p_iv = max(5.0, float(row.get('PE_IV', 13.5))) / 100.0
        sigma = (c_iv + p_iv) / 2.0
        
        try:
            d1 = (math.log(spot / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            cdf_d1, pdf_d1 = norm_cdf(d1), norm_pdf(d1)
            
            # कैलकुलेशन
            c_d, p_d = round(cdf_d1, 2), round(cdf_d1 - 1.0, 2)
            gam = round(pdf_d1 / (spot * sigma * math.sqrt(T)), 5)
            c_th = round((-(spot * pdf_d1 * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm_cdf(d2)) / 365.0, 2)
            p_th = round((-(spot * pdf_d1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365.0, 2)
            veg = round((spot * math.sqrt(T) * pdf_d1) / 100.0, 2)
            van = round(-pdf_d1 * d2 / sigma, 4)
            chm = round(-pdf_d1 * (2 * r * T - d2 * sigma * math.sqrt(T)) / (2 * T * sigma * math.sqrt(T)) / 365.0, 4)
        except:
            c_d, p_d, gam, c_th, p_th, veg, van, chm = 0.5, -0.5, 0.001, -5.0, -5.0, 10.0, 0.01, -0.01

        # डिक्शनरी में अपेंड करें
        results['CE Delta'].append(c_d); results['PE Delta'].append(p_d)
        results['Gamma'].append(gam); results['CE Theta'].append(c_th); results['PE Theta'].append(p_th)
        results['CE Vega'].append(veg); results['PE Vega'].append(veg)
        results['CE Vanna'].append(van); results['PE Vanna'].append(van)
        results['CE Charm'].append(chm); results['PE Charm'].append(chm)
        results['CE GEX (Cr)'].append(round(row.get('Raw_CE_OI', 0) * lot * (spot**2) * gam / 10**8, 2))
        results['PE GEX (Cr)'].append(round(row.get('Raw_PE_OI', 0) * lot * (spot**2) * gam / 10**8, 2))
        results['CE Turnover (Cr)'].append(round((row.get('CE_Volume', 0) * row.get('CE_LTP', 0) * lot) / 10**7, 2))
        results['PE Turnover (Cr)'].append(round((row.get('PE_Volume', 0) * row.get('PE_LTP', 0) * lot) / 10**7, 2))

    # पूरे DataFrame को अपडेट करें
    for col, val in results.items(): df[col] = val
    return df

def get_buildup(chg_oi, pct_chg):
    if pct_chg > 0 and chg_oi > 0: return "Short Build"
    elif pct_chg < 0 and chg_oi < 0: return "Long Unwind"
    elif pct_chg > 0 and chg_oi < 0: return "Short Cover"
    return "Long Build"
