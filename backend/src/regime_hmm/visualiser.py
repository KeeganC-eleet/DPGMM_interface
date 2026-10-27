import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Headless backend: safe for server threads and CLI file output
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from src.regime_hmm.palette import regime_color

# Dark theme colors
BG_COLOR = "#0d1117"
TEXT_COLOR = "#e6edf3"
GRID_COLOR = "#30363d"
PRICE_COLOR = "#e6edf3"

def plot_market_regimes(prices: pd.Series, regimes: pd.Series, ticker: str = "Asset", save_path: str = None):
    """
    Plots the asset price history with background colors corresponding to DPGMM regimes.
    """
    # Align data to ensure indices match perfectly
    df = pd.DataFrame({'Price': prices, 'Regime': regimes}).dropna()
    
    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    
    # Plot the asset price
    ax.plot(df.index, df['Price'], color=PRICE_COLOR, linewidth=1.3, label=f'{ticker} Price', zorder=3)
    
    # Extract unique regimes; colors are keyed by regime id so they match the report
    active_regimes = np.sort(df['Regime'].unique())
    
    # Split the series into runs of the same regime. Each run is shaded until the next run
    # starts, so regime switches and overnight/weekend gaps don't leave unshaded holes.
    run_start = df['Regime'].ne(df['Regime'].shift())
    starts = mdates.date2num(df.index[run_start])
    ends = np.append(starts[1:], mdates.date2num(df.index[-1]))
    run_regimes = df['Regime'][run_start].to_numpy()

    for regime in active_regimes:
        mask = run_regimes == regime
        ax.broken_barh(
            list(zip(starts[mask], ends[mask] - starts[mask])),
            (0, 1),
            transform=ax.get_xaxis_transform(),  # x in data units, y spans the full axes height
            facecolor=regime_color(regime),
            alpha=0.6,
            linewidth=0,
            label=f'Regime {int(regime)}'
        )

    ax.set_title(f"{ticker} Market Regimes (DPGMM)", fontsize=16, fontweight='bold', color=TEXT_COLOR)
    ax.set_ylabel("Price", fontsize=12, color=TEXT_COLOR)
    ax.set_xlabel("Date", fontsize=12, color=TEXT_COLOR)
    ax.set_xlim(df.index[0], df.index[-1])
    ax.tick_params(colors=TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    legend = ax.legend(loc='upper left', bbox_to_anchor=(1, 1), facecolor=BG_COLOR, edgecolor=GRID_COLOR)
    for text in legend.get_texts():
        text.set_color(TEXT_COLOR)
    ax.grid(True, color=GRID_COLOR, alpha=0.6, linestyle='--')
    
    plt.tight_layout()
    
    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        plt.savefig(save_path, dpi=200, facecolor=fig.get_facecolor())
        print(f"Visualization saved to {save_path}")
        
    plt.close(fig)

if __name__ == "__main__":
    print("Visualizer module initialized.")
