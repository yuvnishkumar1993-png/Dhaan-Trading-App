import pandas as pd
import numpy as np
import logging

def process_raw_data(data_dict):
    try:
        if "data" in data_dict and data_dict["data"]:
            df = pd.DataFrame(data_dict["data"])
            if 'close' in df.columns:
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df.dropna(subset=['close'], inplace=True)
            return df
        return None
    except Exception as e:
        logging.error(f"Data Cleaning Error: {str(e)}")
        return None

def calculate_moving_averages(df, price_column='close'):
    if df is not None and price_column in df.columns:
        df['SMA_20'] = df[price_column].rolling(window=20).mean()
        df['EMA_20'] = df[price_column].ewm(span=20, adjust=False).mean()
        df['SMA_50'] = df[price_column].rolling(window=50).mean()
    return df

def calculate_rsi(df, price_column='close', period=14):
    if df is not None and price_column in df.columns:
        delta = df[price_column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
    return df

def calculate_risk_reward(entry_price, stop_loss, target_price, capital, risk_percentage):
    try:
        risk_per_share = abs(entry_price - stop_loss)
        reward_per_share = abs(target_price - entry_price)
        if risk_per_share == 0:
            return {"error": "Stop loss cannot be equal to entry price."}
        risk_reward_ratio = reward_per_share / risk_per_share
        total_risk_amount = capital * (risk_percentage / 100)
        quantity = int(total_risk_amount / risk_per_share)
        return {
            "Quantity": quantity,
            "Risk Per Share": risk_per_share,
            "Reward Per Share": reward_per_share,
            "Risk-Reward Ratio": round(risk_reward_ratio, 2),
            "Total Max Risk": total_risk_amount
        }
    except Exception as e:
        return {"error": str(e)}

def calculate_pcr(chain_df):
    try:
        if 'Call_OI' in chain_df.columns and 'Put_OI' in chain_df.columns:
            total_call_oi = chain_df['Call_OI'].sum()
            total_put_oi = chain_df['Put_OI'].sum()
            if total_call_oi == 0: return 0.0
            return round(total_put_oi / total_call_oi, 2)
        return 1.0
    except Exception as e:
        return 1.0

def calculate_max_pain(chain_df):
    try:
        if 'Strike' not in chain_df.columns or 'Call_OI' not in chain_df.columns or 'Put_OI' not in chain_df.columns:
            return None
        strikes = chain_df['Strike'].values
        call_ois = chain_df['Call_OI'].values
        put_ois = chain_df['Put_OI'].values
        min_pain = float('inf')
        max_pain_strike = strikes[0]
        
        for expiry_price in strikes:
            total_payout = 0
            for i, strike in enumerate(strikes):
                if expiry_price > strike: total_payout += (expiry_price - strike) * call_ois[i]
                if expiry_price < strike: total_payout += (strike - expiry_price) * put_ois[i]
            if total_payout < min_pain:
                min_pain = total_payout
                max_pain_strike = expiry_price
        return max_pain_strike
    except Exception as e:
        return None

def calculate_gex(chain_df, spot_price, lot_size=25):
    try:
        if 'Strike' not in chain_df.columns or 'Call_OI' not in chain_df.columns or 'Put_OI' not in chain_df.columns:
            return 0.0
        net_oi_diff = (chain_df['Call_OI'] - chain_df['Put_OI']).sum()
        gex_value = (net_oi_diff * (spot_price ** 2) * 0.0000001) * lot_size
        return round(gex_value, 2)
    except Exception as e:
        return 0.0

def run_advanced_calculations(data_dict):
    df = process_raw_data(data_dict)
    if df is not None:
        df = calculate_moving_averages(df)
        df = calculate_rsi(df)
        return df
    return None
