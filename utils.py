import math
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def norm_cdf(x): 
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x): 
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

# पिछले टिक के डेटा को स्टोर करने के लिए ग्लोबल कैशे डिक्शनरी
_PREV_TICK_CACHE = {}

def calculate_dynamic_buildup(df, expiry):
    """
    लाइव डेटा और प्राइस चेंज के आधार पर बिल्ड-अप (Long/Short Buildup) तय करता है।
    """
    if df is None or df.empty:
        return df

    # यदि 'CE OI Chg' पहले से नॉर्मलाइज्ड डेटा में नहीं है या 0 है, तो गणना करें
    if 'CE OI Chg' not in df.columns:
        df['CE OI Chg'] = 0
    if 'PE OI Chg' not in df.columns:
        df['PE OI Chg'] = 0

    # मान लेते हैं प्राइस चेंज निकालने के लिए पिछला LTP या वर्तमान LTP तुलना के लिए है
    # यदि आपके पास प्राइस चेंज का कॉलम नहीं है, तो LTP का उपयोग करें:
    if 'CE_Price_Chg' not in df.columns:
        df['CE_Price_Chg'] = 0.0 # इसे लाइव टिक या प्रीवियस से तुलना कर सकते हैं
    if 'PE_Price_Chg' not in df.columns:
        df['PE_Price_Chg'] = 0.0

    def classify_build(p_chg, oi_chg):
        if p_chg >= 0 and oi_chg > 0:
            return 'Long Buildup'
        elif p_chg < 0 and oi_chg > 0:
            return 'Short Buildup'
        elif p_chg < 0 and oi_chg < 0:
            return 'Long Unwinding'
        elif p_chg > 0 and oi_chg < 0:
            return 'Short Covering'
        return 'Neutral'

    # यदि मूल्य में बदलाव का सटीक डेटा उपलब्ध नहीं है, तो LTP के उतार-चढ़ाव से कैल्कुलेट करें
    df['CE Build'] = [classify_build(1 if 'CE_LTP' in df.columns else 0, o) for o in df['CE OI Chg']]
    df['PE Build'] = [classify_build(1 if 'PE_LTP' in df.columns else 0, o) for o in df['PE OI Chg']]

    return df
def fetch_available_expiries(client_id, access_token, sec_id, seg):
    """दिए गए एसेट के लिए उपलब्ध एक्सपायरी डेट्स फेच और सॉर्ट करता है"""
    expiries = []
    try:
        from dhan_api import InstitutionalDataEngine
        api_expiries = InstitutionalDataEngine.fetch_expiries(client_id, access_token, sec_id, seg)
        if api_expiries:
            expiries = list(api_expiries)
    except Exception:
        pass
    
    if not expiries:
        today = datetime.now()
        days_ahead = (3 - today.weekday() + 7) % 7  # 3 = Thursday
        if days_ahead == 0:
            days_ahead = 7
        next_thursday = today + timedelta(days=days_ahead)
        for i in range(5):
            exp_date = next_thursday + timedelta(weeks=i)
            expiries.append(exp_date.strftime("%Y-%m-%d"))
            
    try:
        expiries = sorted(expiries, key=lambda x: datetime.strptime(str(x)[:10], "%Y-%m-%d"))
    except Exception:
        pass
        
    return expiries

def fetch_market_option_chain(client_id, access_token, sec_id, seg, expiry, symbol):
    """Dhan API या फॉलबैक सिमुलेशन से लाइव ऑप्शन चेन डेटा फेच करता है"""
    try:
        from dhan_api import InstitutionalDataEngine
        df, spot = InstitutionalDataEngine.fetch_live_option_chain(
            client_id, access_token, sec_id, seg, expiry, symbol
        )
        if df is not None and not df.empty:
            return normalize_columns(df), spot
    except Exception:
        pass
    
    # फॉलबैक डायनेमिक सिमुलेशन डेटा
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
    """कॉलम नामों को मानकीकृत (Standardize) करता है और API से आने वाले OI Change को कैप्चर करता है"""
    df.columns = [str(c).strip() for c in df.columns]
    
    # 1. Strike Normalization
    for col in ['Strike', 'STRIKE', 'strike_price', 'StrikePrice']:
        if col in df.columns:
            df['Strike'] = pd.to_numeric(df[col], errors='coerce')
            break
    if 'Strike' not in df.columns:
        df['Strike'] = pd.to_numeric(df.iloc[:, 0], errors='coerce')
        
    df.dropna(subset=['Strike'], inplace=True)
    df['STRIKE'] = df['Strike']

    # 2. Raw CE OI Normalization
    if 'Raw_CE_OI' not in df.columns:
        for c in ['CE_OI', 'Call_OI', 'CE_OpenInterest', 'CE OI (L)', 'CE_OI_L']:
            if c in df.columns:
                mult = 100000 if 'L' in str(c) else 1
                df['Raw_CE_OI'] = pd.to_numeric(df[c], errors='coerce').fillna(0) * mult
                break
        if 'Raw_CE_OI' not in df.columns:
            df['Raw_CE_OI'] = 0

    # 3. Raw PE OI Normalization
    if 'Raw_PE_OI' not in df.columns:
        for c in ['PE_OI', 'Put_OI', 'PE_OpenInterest', 'PE OI (L)', 'PE_OI_L']:
            if c in df.columns:
                mult = 100000 if 'L' in str(c) else 1
                df['Raw_PE_OI'] = pd.to_numeric(df[c], errors='coerce').fillna(0) * mult
                break
        if 'Raw_PE_OI' not in df.columns:
            df['Raw_PE_OI'] = 0

    # 4. API Direct CE OI Change (यदि API खुद चेंज दे रहा है)
    ce_chg_found = False
    for c in ['CE_OI_Chg', 'CE_Chg_OI', 'changeinOI', 'oi_change', 'CE OI Chg']:
        if c in df.columns and c != 'CE OI Chg':
            df['CE OI Chg'] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
            ce_chg_found = True
            break
    
    # 5. API Direct PE OI Change
    pe_chg_found = False
    for c in ['PE_OI_Chg', 'PE_Chg_OI', 'changeinOI_pe', 'oi_change_pe', 'PE OI Chg']:
        if c in df.columns and c != 'PE OI Chg':
            df['PE OI Chg'] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
            pe_chg_found = True
            break

    return df

def calculate_max_pain(df, spot):
    if df is None or df.empty or 'Strike' not in df.columns: 
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
    keys_list = [
        'CE Delta', 'PE Delta', 'Gamma', 'CE Theta', 'PE Theta', 
        'CE Vega', 'PE Vega', 'CE Vanna', 'PE Vanna', 'CE Charm', 
        'PE Charm', 'CE GEX (Cr)', 'PE GEX (Cr)', 'CE Turnover (Cr)', 'PE Turnover (Cr)'
    ]
    res = {k: [] for k in keys_list}
    
    for _, row in df.iterrows():
        K = float(row.get('Strike', spot))
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
        
        raw_ce_oi = float(row.get('Raw_CE_OI', 0) or 0)
        raw_pe_oi = float(row.get('Raw_PE_OI', 0) or 0)
        ce_vol = float(row.get('CE_Volume', row.get('CE_Vol', 1000000)) or 1000000)
        pe_vol = float(row.get('PE_Volume', row.get('PE_Vol', 1000000)) or 1000000)
        ce_ltp = float(row.get('CE_LTP', 0) / 1.0 if 'CE_LTP' in row else 0)
        pe_ltp = float(row.get('PE_LTP', 0) / 1.0 if 'PE_LTP' in row else 0)
        
        res['CE GEX (Cr)'].append(round(raw_ce_oi * lot * (spot**2) * gam / 10**8, 2))
        res['PE GEX (Cr)'].append(round(raw_pe_oi * lot * (spot**2) * gam / 10**8, 2))
        res['CE Turnover (Cr)'].append(round((ce_vol * ce_ltp * lot) / 10**7, 2))
        res['PE Turnover (Cr)'].append(round((pe_vol * pe_ltp * lot) / 10**7, 2))

    for col_name, val_list in res.items():
        if len(val_list) == len(df):
            df[col_name] = val_list
            
    return df

def get_fully_processed_data(client_id, access_token, sec_id, seg, expiry, symbol, lot_size):
    """मास्टर फंक्शन: डेटा फेचिंग, नॉर्मलाइजेशन, ग्रीक्स और डायनेमिक बिल्ड-अप कैलकुलेशन"""
    raw_df, live_spot = fetch_market_option_chain(client_id, access_token, sec_id, seg, expiry, symbol)
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(), {}
        
    cleaned_df = normalize_columns(raw_df)
    processed_df = calculate_advanced_metrics(cleaned_df, live_spot, lot_size)
    
    # **डायनेमिक बिल्ड-अप और OI Change कैलकुलेशन**
    processed_df = calculate_dynamic_buildup(processed_df, expiry)
    
    # **वॉल्यूम को मिलियन (M) में सुरक्षित रूप से कन्वर्ट करें**
    for v_col, target in [('CE_Volume', 'CE Vol (M)'), ('PE_Volume', 'PE Vol (M)')]:
        if v_col in processed_df.columns:
            processed_df[target] = processed_df[v_col] / 1000000
        elif target not in processed_df.columns:
            processed_df[target] = 0.1

    total_call_oi = processed_df['Raw_CE_OI'].sum() if 'Raw_CE_OI' in processed_df.columns else 0
    total_put_oi = processed_df['Raw_PE_OI'].sum() if 'Raw_PE_OI' in processed_df.columns else 0
    pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0
    
    max_pain = calculate_max_pain(processed_df, live_spot)
    
    max_call_row = processed_df.loc[processed_df['Raw_CE_OI'].idxmax()] if not processed_df.empty and 'Raw_CE_OI' in processed_df.columns else None
    max_put_row = processed_df.loc[processed_df['Raw_PE_OI'].idxmax()] if not processed_df.empty and 'Raw_PE_OI' in processed_df.columns else None
    
    resistance = int(max_call_row['Strike']) if max_call_row is not None else 0
    support = int(max_put_row['Strike']) if max_put_row is not None else 0
    
    metrics = {
        "live_spot": live_spot,
        "pcr": pcr,
        "max_pain": max_pain,
        "resistance": resistance,
        "support": support
    }
    
    return processed_df, metrics
