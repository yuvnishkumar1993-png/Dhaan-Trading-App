import math
import numpy as np

def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x):
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

def calculate_advanced_metrics(df, spot, lot):
    r, T = 0.06, 2 / 365.0
    ce_deltas, pe_deltas, gammas, ce_thetas, vegas, ce_gexs, pe_gexs = [], [], [], [], [], [], []
    for _, row in df.iterrows():
        K = row['Strike']
        call_oi = row.get('Raw_CE_OI', 0)
        put_oi = row.get('Raw_PE_OI', 0)
        c_iv = max(5.0, row.get('CE_IV', 13.0)) / 100.0
        p_iv = max(5.0, row.get('PE_IV', 13.5)) / 100.0
        sigma = (c_iv + p_iv) / 2.0
        try:
            d1 = (math.log(spot / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            cdf_d1, pdf_d1 = norm_cdf(d1), norm_pdf(d1)
            c_delta, p_delta = round(cdf_d1, 2), round(cdf_d1 - 1.0, 2)
            gamma = round(pdf_d1 / (spot * sigma * math.sqrt(T)), 5)
            c_theta = round((- (spot * pdf_d1 * sigma) / (2 * math.sqrt(T))) / 365.0, 2)
            vega = round((spot * math.sqrt(T) * pdf_d1) / 100.0, 2)
        except Exception:
            c_delta, p_delta, gamma, c_theta, vega = 0.5, -0.5, 0.001, -5.0, 10.0
        ce_gex = round(call_oi * lot * (spot ** 2) * gamma * 0.01 / 100000.0, 2)
        pe_gex = round(put_oi * lot * (spot ** 2) * gamma * 0.01 / 100000.0, 2)
        ce_deltas.append(c_delta); pe_deltas.append(p_delta); gammas.append(gamma)
        ce_thetas.append(c_theta); vegas.append(vega)
        ce_gexs.append(ce_gex); pe_gexs.append(pe_gex)
    df['CE Delta'], df['PE Delta'], df['Gamma'] = ce_deltas, pe_deltas, gammas
    df['CE Theta'], df['CE Vega'] = ce_thetas, vegas
    df['CE GEX (Cr)'], df['PE GEX (Cr)'] = ce_gexs, pe_gexs
    return df

def calculate_max_pain(df, spot):
    strikes, ce_oi, pe_oi = df['Strike'].values, df['Raw_CE_OI'].values, df['Raw_PE_OI'].values
    min_payout, max_pain_strike = float('inf'), strikes[0]
    for exp_price in strikes:
        payout = sum((exp_price - K) * ce_oi[i] if exp_price > K else (K - exp_price) * pe_oi[i] for i, K in enumerate(strikes))
        if payout < min_payout: min_payout, max_pain_strike = payout, exp_price
    return int(max_pain_strike)
