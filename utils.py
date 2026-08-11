def normalize_columns(df):
    """कॉलम नामों को मानकीकृत (Standardize) करता है"""
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Strike', 'STRIKE', 'strike_price', 'StrikePrice']:
        if col in df.columns:
            df['Strike'] = pd.to_numeric(df[col], errors='coerce')
            break
    if 'Strike' not in df.columns:
        df['Strike'] = pd.to_numeric(df.iloc[:, 0], errors='coerce')
        
    df.dropna(subset=['Strike'], inplace=True)
    df['STRIKE'] = df['Strike']

    # --- CE & PE OI Normalization ---
    if 'Raw_CE_OI' not in df.columns:
        for c in ['CE_OI', 'Call_OI', 'CE_OpenInterest', 'CE OI (L)']:
            if c in df.columns:
                mult = 100000 if 'L' in c or 'OI (L)' in c else 1
                df['Raw_CE_OI'] = pd.to_numeric(df[c], errors='coerce').fillna(100000) * mult
                break
        if 'Raw_CE_OI' not in df.columns:
            df['Raw_CE_OI'] = 100000

    if 'Raw_PE_OI' not in df.columns:
        for c in ['PE_OI', 'Put_OI', 'PE_OpenInterest', 'PE OI (L)']:
            if c in df.columns:
                mult = 100000 if 'L' in c or 'OI (L)' in c else 1
                df['Raw_PE_OI'] = pd.to_numeric(df[c], errors='coerce').fillna(100000) * mult
                break
        if 'Raw_PE_OI' not in df.columns:
            df['Raw_PE_OI'] = 100000

    # --- CE & PE Volume Normalization (नया जोड़ा गया) ---
    if 'CE_Volume' not in df.columns:
        for c in ['CE_Vol', 'Volume_CE', 'CEVolume', 'CE Vol']:
            if c in df.columns:
                df['CE_Volume'] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                break
        if 'CE_Volume' not in df.columns:
            df['CE_Volume'] = 1000000  # फॉलबैक वैल्यू

    if 'PE_Volume' not in df.columns:
        for c in ['PE_Vol', 'Volume_PE', 'PEVolume', 'PE Vol']:
            if c in df.columns:
                df['PE_Volume'] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                break
        if 'PE_Volume' not in df.columns:
            df['PE_Volume'] = 1000000  # फॉलबैक वैल्यू

    return df
