"""
Market Regime Analysis Report Generator.
Exports DPGMM market regime classification results, transition matrices,
and feature statistics into a clean, comprehensive Markdown report.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
import numpy as np
import pandas as pd

def _state_label(val: Any) -> str:
    try:
        return f"Regime {int(float(val))}"
    except (ValueError, TypeError):
        return f"Regime {val}"

# Broad-market index funds. Yahoo index symbols (^GSPC, ^NDX, ^DJI, ...) are detected by their ^ prefix.
INDEX_FUNDS = {
    "SPY", "VOO", "IVV", "SPLG", "RSP", "QQQ", "QQQM", "ONEQ", "DIA", "IWM", "IWB", "IWV",
    "VTI", "ITOT", "SCHB", "SCHX", "MDY", "IJH", "IJR", "VT", "ACWI", "VXUS", "EFA", "VEA", "VWO", "EEM",
}

# Annualized % thresholds for the regime descriptor. Indexes are diversified and move far less
# than single stocks, so they use tighter bands to separate trending regimes from neutral ones.
LABEL_THRESHOLDS = {
    "stock": {"return": 10.0, "vol": 25.0},
    "index": {"return": 5.0, "vol": 18.0},
}

def is_index_fund(ticker: Optional[str]) -> bool:
    if not ticker:
        return False
    ticker = ticker.upper()
    return ticker.startswith("^") or ticker in INDEX_FUNDS

def _periods_per_year(index: pd.Index) -> float:
    """Bars per year inferred from the data (252 for daily, ~1,764 for hourly US equities)."""
    if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
        return 252.0
    bars_per_day = pd.Series(1, index=index).groupby(index.normalize()).size().median()
    return 252.0 * max(float(bars_per_day), 1.0)

def _label_regime(ann_return: float, ann_vol: float, thresholds: Optional[dict] = None) -> str:
    if pd.isna(ann_return) or pd.isna(ann_vol):
        return "Unclassified Regime"

    t = thresholds or LABEL_THRESHOLDS["stock"]
    ret_band, vol_high = t["return"], t["vol"]
    
    if ann_return > ret_band and ann_vol < vol_high:
        return "Bull Market (Low Volatility / Steady Expansion)"
    elif ann_return > ret_band and ann_vol >= vol_high:
        return "Bull Market (High Volatility / Momentum Rally)"
    elif ann_return < -ret_band and ann_vol >= vol_high:
        return "Bear Market (High Volatility / Sharp Correction)"
    elif ann_return < -ret_band and ann_vol < vol_high:
        return "Bearish Drift (Contraction / Controlled Downtrend)"
    elif abs(ann_return) <= ret_band and ann_vol >= vol_high:
        return "Turbulent Consolidation (High Volatility / Choppy)"
    else:
        return "Neutral / Range-Bound (Low Volatility Consolidation)"

def format_regime_summary_md(results_df: pd.DataFrame, price_df: Optional[pd.DataFrame] = None, ticker: Optional[str] = None) -> str:
    if 'Regime' not in results_df.columns:
        return "No regime data available.\n"

    total_days = len(results_df)
    active_regimes = sorted(results_df['Regime'].unique())
    periods_per_year = _periods_per_year(results_df.index)
    thresholds = LABEL_THRESHOLDS["index" if is_index_fund(ticker) else "stock"]

    has_return = 'log_return' in results_df.columns
    has_mom = 'momentum_50' in results_df.columns
    has_yield = 'yield_spread' in results_df.columns
    has_tariff = 'tariff_rate' in results_df.columns

    headers = [
        "Regime", "Trading Days", "Frequency (%)", "Ann. Return", 
        "Ann. Volatility", "Sharpe (Rf=0)"
    ]
    if has_mom: headers.append("Mean Mom (50d)")
    if has_yield: headers.append("Yield Spread (10Y-2Y)")
    if has_tariff: headers.append("Tariff Rate (%)")
    headers.append("Regime Characterization")

    alignments = [":---:"] * (len(headers) - 1) + [":---"]
    
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(alignments) + " |"]

    for regime in active_regimes:
        subset = results_df[results_df['Regime'] == regime]
        count = len(subset)
        pct = (count / total_days) * 100

        if has_return:
            # Annualize at the data's real bar frequency so hourly and daily runs are comparable
            mean_ret = subset['log_return'].mean()
            ann_ret = mean_ret * periods_per_year * 100
            ret_str = f"{ann_ret:+.2f}%"
            
            # A single-bar regime has no measurable volatility; leave it unclassified
            std_ret = subset['log_return'].std()
            ann_vol = std_ret * np.sqrt(periods_per_year) * 100 if not np.isnan(std_ret) else np.nan
            vol_str = f"{ann_vol:.2f}%" if not np.isnan(ann_vol) else "N/A"

            sharpe = (ann_ret / ann_vol) if (ann_vol > 0.001 and not pd.isna(ann_ret)) else np.nan
            sharpe_str = f"{sharpe:.2f}" if not np.isnan(sharpe) else "N/A"
        else:
            ann_ret = 0.0
            ann_vol = 0.0
            ret_str = vol_str = sharpe_str = "N/A"

        row = [f"**{_state_label(regime)}**", f"{count:,}", f"{pct:.1f}%", ret_str, vol_str, sharpe_str]

        if has_mom: row.append(f"{subset['momentum_50'].mean() * 100:+.2f}%")
        if has_yield: row.append(f"{subset['yield_spread'].mean():.2f}%")
        if has_tariff: row.append(f"{subset['tariff_rate'].mean():.2f}%")

        row.append(_label_regime(ann_ret, ann_vol, thresholds))
        lines.append("| " + " | ".join(row) + " |")

    profile = "index fund" if is_index_fund(ticker) else "single stock"
    lines += [
        "",
        f"> Characterization thresholds ({profile}): trending when annualized return is beyond "
        f"**±{thresholds['return']:.0f}%**, high volatility at **{thresholds['vol']:.0f}%+** annualized. "
        f"Figures annualized from {periods_per_year:,.0f} bars per year.",
    ]
    return "\n".join(lines) + "\n"

def format_transition_matrix_md(trans_matrix: pd.DataFrame) -> str:
    if trans_matrix is None or trans_matrix.empty:
        return "Transition matrix not available.\n"

    headers = ["Current \\ Next"] + [_state_label(col) for col in trans_matrix.columns]
    alignments = [":---"] + [":---:"] * len(trans_matrix.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(alignments) + " |"]

    for curr_state, row in trans_matrix.iterrows():
        row_cells = [f"**{_state_label(curr_state)}**"]
        for next_state in trans_matrix.columns:
            prob = row.get(next_state, 0.0)
            formatted = f"{prob * 100:.2f}%"
            row_cells.append(f"**{formatted}**" if curr_state == next_state else formatted)
        lines.append("| " + " | ".join(row_cells) + " |")

    return "\n".join(lines) + "\n"

def format_persistence_table_md(trans_matrix: pd.DataFrame) -> str:
    if trans_matrix is None or trans_matrix.empty: return ""

    headers = ["Regime", "Persistence P(S|S)", "Expected Duration (Days)", "Primary Exit Destination", "Exit Prob (%)"]
    alignments = [":---:", ":---:", ":---:", ":---:", ":---:"]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(alignments) + " |"]

    for state in trans_matrix.index:
        p_stay = trans_matrix.loc[state, state] if state in trans_matrix.columns else 0.0
        days_str = f"{1.0 / (1.0 - p_stay):.1f} days" if p_stay < 0.9999 else "Absorbing (>1000 days)"

        other_states = [s for s in trans_matrix.columns if s != state]
        if other_states:
            exit_sub = trans_matrix.loc[state, other_states]
            best_exit_str, prob_str = _state_label(exit_sub.idxmax()), f"{exit_sub.max() * 100:.2f}%"
        else:
            best_exit_str, prob_str = "None", "0.00%"

        lines.append(f"| {_state_label(state)} | {p_stay * 100:.2f}% | {days_str} | {best_exit_str} | {prob_str} |")

    return "\n".join(lines) + "\n"

def format_feature_statistics_md(features_df: pd.DataFrame) -> str:
    if features_df is None or features_df.empty: return "No feature data available.\n"
    desc = features_df.describe().T
    headers = ["Feature", "Count", "Mean", "Std Dev", "Min", "25%", "Median", "75%", "Max"]
    alignments = [":---"] + [":---:"] * 8
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(alignments) + " |"]

    for feat_name, stats in desc.iterrows():
        if feat_name == "Regime": continue
        row = [f"`{feat_name}`", f"{int(stats['count']):,}", f"{stats['mean']:.4f}", f"{stats['std']:.4f}", f"{stats['min']:.4f}", f"{stats['25%']:.4f}", f"{stats['50%']:.4f}", f"{stats['75%']:.4f}", f"{stats['max']:.4f}"]
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines) + "\n"

def write_markdown_report(
    ticker: str, start_date: str, end_date: str, results_df: pd.DataFrame,
    trans_matrix: Optional[pd.DataFrame] = None, model: Optional[Any] = None,
    price_df: Optional[pd.DataFrame] = None, features_df: Optional[pd.DataFrame] = None,
    output_dir: str = "models", plot_filename: Optional[str] = None,
    base_dir: str = ".", **kwargs
) -> str:
    
    start_date = start_date or kwargs.get("start", "")
    end_date = end_date or kwargs.get("end", "")

    target_dir = Path(base_dir) / "models" if output_dir == "/models" else Path(base_dir) / output_dir if not os.path.isabs(output_dir) else Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    custom_filename = kwargs.get("report_filename")
    md_filepath = target_dir / custom_filename if custom_filename else target_dir / f"{ticker}_{start_date}_{end_date}.md"
    plot_filename = plot_filename or f"{ticker}_regime_plot.png"

    latest_regime = int(results_df['Regime'].iloc[-1]) if results_df is not None and not results_df.empty else None
    latest_date_str = results_df.index[-1].strftime('%Y-%m-%d') if latest_regime is not None else "N/A"
    
    latest_price_str = "N/A"
    if latest_regime is not None and price_df is not None and results_df.index[-1] in price_df.index:
        close_val = price_df.loc[results_df.index[-1], 'Close']
        latest_price_str = f"${float(close_val.iloc[0] if isinstance(close_val, pd.Series) else close_val):.2f}"

    # NEW: Determine model architecture and parameters dynamically
    is_fat_tail = kwargs.get('is_fat_tail', False)
    model_framework = "Student's t-Mixture Model (PyMC Fat Tails)" if is_fat_tail else "Dirichlet Process Gaussian Mixture Model (DPGMM)"
    
    max_regimes = getattr(model, 'max_regimes', 'N/A')

    # Artifact paths (overridable so per-generation output dirs are reported correctly)
    model_prefix = 'fat' if is_fat_tail else 'gaussian'
    model_path = kwargs.get('model_path') or f"models/dpgmm_{model_prefix}.joblib"
    data_path = kwargs.get('data_path') or f"data/processed/{ticker}_labeled_{model_prefix}.csv"
    plot_path = kwargs.get('plot_path') or f"models/{plot_filename}"

    # Optional live options section; when present, visualizations become section 7
    options_section = kwargs.get('options_section')
    options_plot_path = kwargs.get('options_plot_path')
    viz_section = 7 if options_section else 6
    
    if is_fat_tail and hasattr(model, 'weight_prior'):
        weight_prior = f"{model.weight_prior}"
    elif not is_fat_tail and model is not None and hasattr(model, 'model') and hasattr(model.model, 'weight_concentration_prior'):
        weight_prior = f"{model.model.weight_concentration_prior}"
    else:
        weight_prior = "N/A"

    content_parts = [
        f"# Market Regime Analysis: {ticker}", "",
        f"> **Automated Quantitative Intelligence Report**  ",
        f"> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | **Project Directory:** `{output_dir}`", "",
        f"---", "", f"## 1. Executive Summary", "",
        f"| Parameter | Configuration / Result |", f"| :--- | :--- |",
        f"| **Ticker Symbol** | `{ticker}` |", f"| **Analysis Range** | `{start_date}` to `{end_date}` |",
        f"| **Total Trading Observations** | `{len(results_df):,}` periods |",
        f"| **Asset Profile** | {'Index fund (tighter regime thresholds)' if is_index_fund(ticker) else 'Single stock'} |",
        f"| **Model Framework** | {model_framework} |",
        f"| **Prior Upper Bound Regimes** | `{max_regimes}` |",
        f"| **Weight Concentration Prior (γ)** | `{weight_prior}` |",
        f"| **Active Regimes Discovered** | **`{len(results_df['Regime'].unique()) if results_df is not None else 0}` regimes** |",
        f"| **Latest Trading Date** | `{latest_date_str}` |", f"| **Latest Asset Price** | `{latest_price_str}` |",
        f"| **Current Identified Regime** | **{_state_label(latest_regime)}** |", "", "---", "",
        f"## 2. Current Market Outlook & Transition Forecast", "",
        f"As of **{latest_date_str}**, `{ticker}` is operating in **{_state_label(latest_regime)}**."
    ]

    if trans_matrix is not None and latest_regime in trans_matrix.index:
        p_stay = trans_matrix.loc[latest_regime, latest_regime] if latest_regime in trans_matrix.columns else 0.0
        content_parts.extend(["", f"- **Regime Stability:** There is a **{p_stay * 100:.2f}%** probability that the asset remains in **{_state_label(latest_regime)}** tomorrow.", "- **Next-Day State Probability Distribution:**"])
        for next_st in sorted(trans_matrix.columns):
            if (prob := trans_matrix.loc[latest_regime, next_st]) > 0.001:
                content_parts.append(f"  - $\\rightarrow$ **{_state_label(next_st)}**: `{prob * 100:.2f}%`")
    
    content_parts.extend([
        "", "---", "", f"## 3. Market Regime Distribution & Statistical Profiles", "",
        format_regime_summary_md(results_df, price_df, ticker), "", "---", "",
        f"## 4. Empirical Transition Probability Matrix", "", format_transition_matrix_md(trans_matrix), "",
        f"### Regime Persistence & Expected Dwell Times", "", format_persistence_table_md(trans_matrix), "", "---", "",
        f"## 5. Feature Engineering & Dataset Summary", "", format_feature_statistics_md(features_df if features_df is not None else results_df), "", "---", "",
        *([options_section, "", "---", ""] if options_section else []),
        f"## {viz_section}. Visualizations & Model Artifacts", "", f"![{ticker} Market Regimes]({plot_filename})", "",
        f"### Artifact Inventory", "", f"| Artifact Description | Path |", f"| :--- | :--- |",
        f"| **Markdown Analysis Report** | `{kwargs.get('report_path') or md_filepath}` |",
        f"| **Fitted Model & Scaler Bundle** | `{model_path}` |",
        f"| **Labeled Feature Dataset** | `{data_path}` |",
        f"| **Regime Price Visualization** | `{plot_path}` |",
        *([f"| **Short-Dated Options Visualization** | `{options_plot_path}` |"] if options_plot_path else []), "", "---", f"*Report produced by Dirichlet Process Regime Engine.*"
    ])

    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(content_parts) + "\n")

    return str(md_filepath)

if __name__ == "__main__":
    print("outputFileWrite module loaded successfully.")