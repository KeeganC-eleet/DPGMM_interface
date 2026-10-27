import os
import pandas as pd
import yfinance as yf
import requests
import wbgapi as wb
from fredapi import Fred
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the .env file in the project root
load_dotenv()

# Initialize API Keys
FMP_API_KEY = os.getenv("FMP_API_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")

# Initialize FRED client if the key is available
if FRED_API_KEY:
    fred = Fred(api_key=FRED_API_KEY)

def load_ticker_data(ticker: str, start_date: str, end_date: str, interval: str = "1d", base_dir: str = ".") -> pd.DataFrame:
    """Fetches and caches pricing data from Yahoo Finance."""
    raw_dir = Path(base_dir) / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cache_file = raw_dir / f"{ticker}_{interval}_{start_date}_{end_date}.csv"
    
    if cache_file.exists():
        return pd.read_csv(cache_file, index_col=0, parse_dates=True)

    print(f"Downloading {ticker} price data from Yahoo Finance...")
    df = yf.download(ticker, start=start_date, end=end_date, interval=interval, progress=False)
    
    # NEW: Flatten the yfinance MultiIndex columns before caching
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df = df.dropna()
    
    if isinstance(df.index, pd.DatetimeIndex):
        df.index = df.index.tz_localize(None)
        
    # Don't cache empty downloads (bad ticker or transient failure) so a retry can succeed
    if not df.empty:
        df.to_csv(cache_file)
    return df

def load_fmp_capex(ticker: str) -> pd.DataFrame:
    """Fetches annual capital expenditure data via Financial Modeling Prep."""
    if not FMP_API_KEY:
        raise ValueError("FMP_API_KEY is missing from .env")
        
    print(f"Downloading CAPEX data for {ticker} from FMP...")
    url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?apikey={FMP_API_KEY}&limit=20"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise ConnectionError(f"Failed to fetch FMP data: {response.text}")
        
    data = response.json()
    df = pd.DataFrame(data)
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df = df[['capitalExpenditure']]
        df = df.sort_index()
        
    return df

def load_fred_macro(series_id: str, start_date: str, end_date: str) -> pd.Series:
    """
    Fetches macroeconomic time series from FRED. 
    Common series IDs:
    - 'DGS10': 10-Year Treasury Constant Maturity Rate
    - 'T10Y2Y': 10-Year minus 2-Year Treasury Yield Spread
    """
    if not FRED_API_KEY:
        raise ValueError("FRED_API_KEY is missing from .env")
        
    print(f"Downloading FRED macro series {series_id}...")
    data = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
    data.index = pd.to_datetime(data.index)
    data = data.dropna()
    return data

def load_worldbank_trade_data(indicator: str = 'TM.TAX.MRCH.SM.AR.ZS', country: str = 'USA') -> pd.DataFrame:
    """
    Fetches World Bank data without an API key using wbgapi.
    Default indicator: Tariff rate, applied, simple mean, all products (%).
    """
    print(f"Downloading World Bank indicator {indicator} for {country}...")
    # Fetch data for the last 20 years
    df = wb.data.DataFrame(indicator, country, time=range(2004, 2025))
    
    # Transpose so years are rows, matching standard time-series formats
    df = df.T
    df.index = df.index.str.replace('YR', '')
    df.index = pd.to_datetime(df.index, format='%Y')
    df.columns = [indicator]
    
    return df.dropna()

if __name__ == "__main__":
    # Test execution for macro and fundamental endpoints
    capex_df = load_fmp_capex("AAPL")
    print("\nApple CAPEX:")
    print(capex_df.head())
    
    yield_spread = load_fred_macro("T10Y2Y", "2020-01-01", "2024-01-01")
    print("\n10Y-2Y Yield Spread:")
    print(yield_spread.head())
    
    tariffs = load_worldbank_trade_data()
    print("\nUS Applied Tariffs:")
    print(tariffs.head())