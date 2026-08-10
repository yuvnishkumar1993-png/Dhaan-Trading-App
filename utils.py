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
    
    # डिक्शनरी आधारित सेफ स्ट्रक्चर ताकि NameError कभी न आए
    res = {k: [] for k in [
        'CE Delta', 'PE Delta', 'Gamma', 'CE Theta', 'PE Theta', 
        'CE Vega', 'PE Vega', 'CE Vanna', 'PE Vanna', 'CE Charm', 
        'PE Charm', 'CE GEX (Cr)', 'PE GEX (Cr)', 'CE Turnover (Cr)', 'PE Turnover (Cr)'
    ]}
    
    for _, row in df.iterrows():
        K = float(row.get('Strike', spot))
        c_iv = max(5.0, float(row.get('CE_IV', 13.0))) / 100.0
        p_iv = max(5.0, float(row.get('PE_IV', 13.5))) / 100.0
        sigma = (c_iv + p_iv) / 2.0
        
        # डिफॉल्ट सेफ वैल्यूज
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
        
        raw_ce_oi = float(row.get('Raw_CE_OI', 0) or 0)
        raw_pe_oi = float(row.get('Raw_PE_OI', 0) or 0)
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

def get_buildup(chg_oi, pct_chg):
    if pct_chg > 0 and chg_oi > 0: return "Short Build"
    elif pct_chg < 0 and chg_oi < 0: return "Long Unwind"
    elif pct_chg > 0 and chg_oi < 0: return "Short Cover"
    return "Long Build"
import pandas as pd
import numpy as np

def calculate_max_pain(df_chain):
    """
    ऑप्शन चेन डेटा के आधार पर Max Pain स्ट्राइक प्राइस की गणना करता है।
    """
    if df_chain.empty or 'StrikePrice' not in df_chain.columns:
        return None
    
    strikes = df_chain['StrikePrice'].values
    ce_oi = df_chain['CE_OpenInterest'].values if 'CE_OpenInterest' in df_chain.columns else np.zeros(len(strikes))
    pe_oi = df_chain['PE_OpenInterest'].values if 'PE_OpenInterest' in df_chain.columns else np.zeros(len(strikes))
    
    total_pain = []
    
    for expiry_strike in strikes:
        pain = 0
        for i, strike in enumerate(strikes):
            # Call writers' loss if market expires at expiry_strike
            if expiry_strike > strike:
                pain += (expiry_strike - strike) * ce_oi[i]
            # Put writers' loss if market expires at expiry_strike
            if expiry_strike < strike:
                pain += (strike - expiry_strike) * pe_oi[i]
        total_pain.append(pain)
        
    min_pain_index = np.argmin(total_pain)
    return strikes[min_pain_index]


def detect_oi_spurt(df_chain, threshold=100000):
    """
    ओपन इंटरेस्ट (OI) में अचानक आए उछाल (Spurt) या अनवाइंडिंग को डिटेक्ट करता है।
    """
    if df_chain.empty:
        return pd.DataFrame()
    
    # यदि डेटा में Change in OI का कॉलम है, तो उसका उपयोग करें
    if 'Change_in_OI' in df_chain.columns:
        spurt_df = df_chain[abs(df_chain['Change_in_OI']) >= threshold]
        return spurt_df
    
    return pd.DataFrame()


def calculate_strategy_payoff(strategy_name, strike_1, strike_2, premium_1, premium_2, spot_range):
    """
    विभिन्न ऑप्शन रणनीतियों (जैसे Bull Call Spread, Straddle) के लिए Payoff (Profit/Loss) कैलकुलेट करता है।
    """
    payoffs = []
    
    for spot in spot_range:
        pnl = 0
        if strategy_name == "Bull Call Spread":
            # Long Lower Strike CE, Short Higher Strike CE
            long_ce_pnl = max(0, spot - strike_1) - premium_1
            short_ce_pnl = premium_2 - max(0, spot - strike_2)
            pnl = (long_ce_pnl + short_ce_pnl) * 50  # Lot size multiplier (e.g., Nifty 50)
            
        elif strategy_name == "Long Straddle":
            # Buy ATM CE and Buy ATM PE
            ce_pnl = max(0, spot - strike_1) - premium_1
            pe_pnl = max(0, strike_1 - spot) - premium_2
            pnl = (ce_pnl + pe_pnl) * 50
            
        payoffs.append(pnl)
        
    return pd.DataFrame({'SpotPrice': spot_range, 'PnL': payoffs})


def get_multi_expiry_matrix():
    """
    मल्टी-एक्सपायरी डेटा स्ट्रक्चर को मैनेज करने के लिए डमी/लाइव स्ट्रक्चर।
    """
    expiries = ["Current Weekly", "Next Weekly", "Current Monthly"]
    return expiries
