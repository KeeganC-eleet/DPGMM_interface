import numpy as np
import pandas as pd

def _align_macro(macro_series: pd.Series, target_index: pd.DatetimeIndex) -> pd.Series:
    """Combines dates before forward-filling to prevent losing historical anchors."""
    combined_dates = target_index.union(macro_series.index).sort_values().drop_duplicates()
    filled_series = macro_series.reindex(combined_dates).ffill()
    return filled_series.loc[target_index]

def calculate_hmm_features(
    price_df: pd.DataFrame, 
    yield_series: pd.Series = None,
    capex_df: pd.DataFrame = None, 
    tariff_df: pd.DataFrame = None,
    vol_window: int = 14
) -> pd.DataFrame:
    
    if price_df.empty:
        raise ValueError("Price data is empty. Adjust your start_date to respect Yahoo Finance interval limits.")
        
    features = pd.DataFrame(index=price_df.index)
    
    # 1. Price Action Features
    features['log_return'] = np.log(price_df['Close'] / price_df['Close'].shift(1))
    features['volatility'] = features['log_return'].rolling(window=vol_window).std() * np.sqrt(252)
    
    # NEW: Momentum Indicator (Distance from 50-period moving average)
    features['momentum_50'] = (price_df['Close'] / price_df['Close'].rolling(window=50).mean()) - 1
    
    daily_index = features.index.normalize()
    # ... (macro alignment logic remains exactly the same below this)

    if yield_series is not None and not yield_series.empty:
        aligned_yield = _align_macro(yield_series, daily_index)
        aligned_yield.index = features.index
        features['yield_spread'] = aligned_yield
        
    if capex_df is not None and not capex_df.empty:
        capex_growth = capex_df['capitalExpenditure'].pct_change()
        aligned_capex = _align_macro(capex_growth, daily_index)
        aligned_capex.index = features.index
        features['capex_growth'] = aligned_capex
        
    if tariff_df is not None and not tariff_df.empty:
        tariff_col = tariff_df.columns[0]
        aligned_tariff = _align_macro(tariff_df[tariff_col], daily_index)
        aligned_tariff.index = features.index
        features['tariff_rate'] = aligned_tariff
        
    # Drop rows containing NaNs (primarily the first 14 days due to the volatility rolling window)
    return features.dropna()