import math
import pandas as pd
import numpy as np

def norm_cdf(x): 
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x): 
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

def get_option_chain_data():
    """
    Dhan API या फॉलबैक से ऑप्शन चेन डेटा फेच करता है। 
    यदि लाइव डेटा उपलब्ध नहीं है या मार्केट बंद है, तो यह टेस्टिंग के लिएफ सेफ डमी डेटा रिटर्न करता है।
    """
    try:
        # यहाँ आप अपने धन एपीआई (dhan_api.py) के असली कॉल को जोड़ सकते हैं
        # फिलहाल ऐप क्रैश न हो, इसके लिए मजबूत स्ट्रक्चर वाला डेटा:
        data = {
            'StrikePrice': [24300, 24350, 24400, 24450, 24500, 24550, 24600, 24650, 24700],
            'CE_OpenInterest': [150000, 230000, 500000, 800000, 1200000, 900000, 600000, 300000, 100000],
            'PE_OpenInterest': [1100000, 950000, 800000, 600000, 1100000, 400000, 250000, 150000, 50000],
            'Change_in_OI': [12000, -5000, 45000, -10000, 85000, -20000, 15000, -5000, 2000],
            'CE_Volume': [50000, 80000, 150000, 200000, 350000, 250000, 180000, 90000, 40000],
            'PE_Volume': [300000, 250000, 200000, 150000, 300000, 120000, 80000, 40000, 20000],
            'CE_LTP': [250.5, 210.0, 175.2, 130.0, 95.5, 65.2, 40.0, 22.5, 12.0],
            'PE_LTP': [15.0, 25.0, 45.0, 75.0, 105.0, 145.0, 190.0, 240.0, 300.0],
            'CE_IV': [13.2, 13.0, 12.8, 13.1, 13.5, 13.8, 14.0, 14.5, 15.0],
            'PE_IV': [14.0, 13.7, 13.5, 13.2, 13.0, 13.3, 13.6, 14.1, 14.6]
        }
        df = pd.DataFrame(data)
        # बैकवर्ड कंपैटिबिलिटी के लिए 'Strike' कॉलम भी जोड़ देते हैं
        df['Strike'] = df['StrikePrice']
        df['Raw_CE_OI'] = df['CE_OpenInterest']
        df['Raw_PE_OI'] = df['PE_OpenInterest']
        return df
    except Exception as e:
        return pd.DataFrame()

def calculate_max_pain(df, spot=0):
    if df is None or df.empty:
        return int(spot) if spot else None
    
    strike_col = 'Strike' if 'Strike' in df.columns else 'StrikePrice' if 'StrikePrice' in df.columns else None
    ce_col = 'Raw_CE_OI' if 'Raw_CE_OI' in df.columns else 'CE_OpenInterest' if 'CE_OpenInterest' in df.columns else None
    pe_col = 'Raw_PE_OI' if 'Raw_PE_OI' in df.columns else 'PE_OpenInterest' if 'PE_OpenInterest' in df.columns else None
    
    if not strike_col or not ce_col or not pe_col:
        return int(spot) if spot else None
        
    strikes = df[strike_col].values
    ce_oi = df[ce_col].values
    pe_oi = df[pe_col].values
    
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

def detect_oi_spurt(df_chain, threshold=100000):
    if df_chain is None or df_chain.empty:
        return pd.DataFrame()
    if 'Change_in_OI' in df_chain.columns:
        return df_chain[abs(df_chain['Change_in_OI']) >= threshold]
    return pd.DataFrame()

def calculate_strategy_payoff(strategy_name, strike_1, strike_2, premium_1, premium_2, spot_range):
    payoffs = []
    for spot in spot_range:
        pnl = 0
        if strategy_name == "Bull Call Spread":
            long_ce_pnl = max(0, spot - strike_1) - premium_1
            short_ce_pnl = premium_2 - max(0, spot - strike_2)
            pnl = (long_ce_pnl + short_ce_pnl) * 50
        elif strategy_name == "Long Straddle":
            ce_pnl = max(0, spot - strike_1) - premium_1
            pe_pnl = max(0, strike_1 - spot) - premium_2
            pnl = (ce_pnl + pe_pnl) * 50
        payoffs.append(pnl)
    return pd.DataFrame({'SpotPrice': spot_range, 'PnL': payoffs})

def get_multi_expiry_matrix():
    return ["Current Weekly", "Next Weekly", "Current Monthly"]

def get_buildup(chg_oi, pct_chg):
    if pct_chg > 0 and chg_oi > 0: 
        return "Short Build"
    elif pct_chg < 0 and chg_oi < 0: 
        return "Long Unwind"
    elif pct_chg > 0 and chg_oi < 0: 
        return "Short Cover"
    return "Long Build"

def calculate_advanced_metrics(df, spot, lot):
    if df is None or df.empty or ('Strike' not in df.columns and 'StrikePrice' not in df.columns): 
        return df
        
    r, T = 0.06, 2 / 365.0
    strike_key = 'Strike' if 'Strike' in df.columns else 'StrikePrice'
    
    res = {k: [] for k in [
        'CE Delta', 'PE Delta', 'Gamma', 'CE Theta', 'PE Theta', 
        'CE Vega', 'PE Vega', 'CE Vanna', 'PE Vanna', 'CE Charm', 
        'PE Charm', 'CE GEX (Cr)', 'PE GEX (Cr)', 'CE Turnover (Cr)', 'PE Turnover (Cr)'
    ]}
    
    for _, row in df.iterrows():
        K = float(row.get(strike_key, spot))
        c_iv = max(5.0, float(row.get('CE_IV', 13.0))) / 100.0
        p_iv = max(5.0, float(row.get('PE_IV', 13.5))) / 100.0
        sigma = (c_iv + p_iv) / 2.0
        
        cd, pd_val, gam, cth, pth, veg, van, chm = 0.5, -0.5, 0.001, -5.0, -5.0, 10.0, 0.01, -0.01
        
        try:
            if spot > 0 and K > 0 and sigma > 0 and T > 0:
                d1 = (math.log(spot / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
                d2 = d1 - sigma * math.sqrt(T)
                cdf_d1, pdf_d1 = norm_cdf(d1), norm_pdf(d1)
                
                cd = round(cdf_d1, 2)
                pd_val = round(cdf_d1 - 1.0, 2)
                gam = round(pdf_d1 / (spot * sigma * math.sqrt(T)), 5)
                cth = round((-(spot * pdf_d1 * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm_cdf(d2)) / 365.0, 2)
                pth = round((-(spot * pdf_d1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365.0, 2)
                veg = round((spot * math.sqrt(T) * pdf_d1) / 100.0, 2)
                van = round(-pdf_d1 * d2 / sigma, 4)
                chm = round(-pdf_d1 * (2 * r * T - d2 * sigma * math.sqrt(T)) / (2 * T * sigma * math.sqrt(T)) / 365.0, 4)
        except Exception:
            pass

        res['CE Delta'].append(cd)
        res['PE Delta'].append(pd_val)
        res['Gamma'].append(gam)
        res['CE Theta'].append(cth)
        res['PE Theta'].append(pth)
        res['CE Vega'].append(veg)
        res['PE Vega'].append(veg)
        res['CE Vanna'].append(van)
        res['PE Vanna'].append(van)
        res['CE Charm'].append(chm)
        res['PE Charm'].append(chm)
        
        raw_ce_oi = float(row.get('Raw_CE_OI', row.get('CE_OpenInterest', 0)) or 0)
        raw_pe_oi = float(row.get('Raw_PE_OI', row.get('PE_OpenInterest', 0)) or 0)
        ce_vol = float(row.get('CE_Volume', 0) or 0)
        pe_vol = float(row.get('PE_Volume', 0) or 0)
        ce_ltp = float(row.get('CE_LTP', 0) or 0)
        pe_ltp = float(row.get('PE_LTP', 0) or 0)
        
        res['CE GEX (Cr)'].append(round(raw_ce_oi * lot * (spot**2) * gam / 10**8, 2))
        res['PE GEX (Cr)'].append(round(raw_pe_oi * lot * (spot**2) * gam / 10**8, 2))
        res['CE Turnover (Cr)'].append(round((ce_vol * ce_ltp * lot) / 10**7, 2))
        res['PE Turnover (Cr)'].append(round((pe_vol * pe_ltp * lot) / 10**7, 2))

    for col_name, val_list in res.items():
        df[col_name] = val_list
        
    return df
