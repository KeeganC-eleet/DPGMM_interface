"""
End-to-end market regime pipeline.
Shared by the CLI (main.py) and the API (api/app.py).
"""

import os
import pandas as pd
from pathlib import Path
from src.regime_hmm.visualiser import plot_market_regimes
from src.regime_hmm.model import RegimeDPGMM, calculate_transition_matrix
from src.regime_hmm.outputFileWrite import write_markdown_report
from src.regime_hmm.data_loader import (
    load_ticker_data,
    load_fmp_capex,
    load_fred_macro,
    load_worldbank_trade_data
)
from src.regime_hmm.features import calculate_hmm_features
from src.regime_hmm.options import build_options_section, OPTIONS_PLOT_FILENAME

PLOT_FILENAME = "plot.png"
REPORT_FILENAME = "report.md"
MODEL_FILENAME = "model.joblib"
DATA_FILENAME = "labeled.csv"

def run_analysis(
    ticker: str,
    start_date: str,
    end_date: str,
    max_regimes: int = 3,
    fat_tail: bool = False,
    out_dir: str = "generations",
    base_dir: str = ".",
    interval: str = "1h",
) -> dict:
    """Runs data extraction, feature engineering, model fitting, plotting and reporting.

    All artifacts are written to out_dir. Returns a summary of the discovered regimes.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"Executing Market Regime Analysis for {ticker} (max_regimes={max_regimes})...")

    print("\n=== Phase 1: Data Extraction ===")
    price_df = load_ticker_data(ticker, start_date, end_date, interval=interval, base_dir=base_dir)

    try:
        capex_df = load_fmp_capex(ticker)
    except Exception as e:
        print(f"⚠️ Skipping CAPEX data (Check .env FMP_API_KEY): {e}")
        capex_df = None

    try:
        yield_series = load_fred_macro("T10Y2Y", start_date, end_date)
    except Exception as e:
        print(f"⚠️ Skipping FRED data: {e}")
        yield_series = None

    try:
        tariff_df = load_worldbank_trade_data(country='USA')
    except Exception as e:
        print(f"⚠️ Skipping World Bank data: {e}")
        tariff_df = None

    print("\n=== Phase 2: Feature Engineering & Alignment ===")
    features_df = calculate_hmm_features(
        price_df=price_df, yield_series=yield_series, capex_df=capex_df,
        tariff_df=tariff_df, vol_window=14
    )
    print(f"Successfully aligned {len(features_df.columns)} features over {len(features_df)} trading days.")

    print("\n=== Phase 3: Model Training ===")
    if fat_tail:
        from src.regime_hmm.model2 import RegimeDPGMMFat
        print(f"Initializing PyMC Student's t-Mixture Model with max_regimes = {max_regimes}...")
        hmm_model = RegimeDPGMMFat(max_regimes=max_regimes, weight_prior=0.001)
    else:
        print(f"Initializing scikit-learn DPGMM with max_regimes = {max_regimes}...")
        hmm_model = RegimeDPGMM(max_regimes=max_regimes, weight_prior=0.001, random_state=42)

    hmm_model.fit(features_df)
    regimes = hmm_model.predict(features_df)

    results_df = features_df.copy()
    results_df['Regime'] = regimes

    print("\n=== Phase 4: Output & Serialization ===")
    print("Market Regime Distribution (Trading Days per State):")
    print(results_df['Regime'].value_counts().sort_index())

    model_path = out_path / MODEL_FILENAME
    hmm_model.save_model(str(model_path))

    data_path = out_path / DATA_FILENAME
    results_df.to_csv(data_path)

    print("\n=== Phase 5: Visualization ===")
    aligned_prices = price_df.loc[results_df.index, 'Close'].squeeze()
    plot_path = out_path / PLOT_FILENAME
    plot_market_regimes(aligned_prices, results_df['Regime'], ticker=ticker, save_path=str(plot_path))

    print("\n=== Phase 5b: Options & Volatility Analysis ===")
    options_section, has_options_plot = build_options_section(ticker, price_df, str(out_path), end_date)

    print("\n=== Empirical Transition Matrix ===")
    trans_matrix = calculate_transition_matrix(results_df['Regime'])
    pd.options.display.float_format = '{:.2%}'.format
    print(trans_matrix)
    pd.options.display.float_format = None

    print("\n=== Phase 6: Markdown Report Generation ===")
    report_path = write_markdown_report(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        results_df=results_df,
        trans_matrix=trans_matrix,
        model=hmm_model,
        price_df=price_df,
        features_df=features_df,
        output_dir=os.path.relpath(out_path, base_dir),
        plot_filename=PLOT_FILENAME,
        report_filename=REPORT_FILENAME,
        base_dir=base_dir,
        is_fat_tail=fat_tail,
        model_path=os.path.relpath(model_path, base_dir),
        data_path=os.path.relpath(data_path, base_dir),
        plot_path=os.path.relpath(plot_path, base_dir),
        report_path=os.path.relpath(out_path / REPORT_FILENAME, base_dir),
        options_section=options_section,
        options_plot_path=os.path.relpath(out_path / OPTIONS_PLOT_FILENAME, base_dir) if has_options_plot else None,
    )
    print(f"Markdown report generated: {report_path}")

    return {
        "regimes": sorted(int(r) for r in results_df['Regime'].unique()),
        "current_regime": int(results_df['Regime'].iloc[-1]),
        "observations": len(results_df),
        "report_path": str(report_path),
        "plot_path": str(plot_path),
    }
