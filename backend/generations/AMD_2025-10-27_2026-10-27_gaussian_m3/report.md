# Market Regime Analysis: AMD

> **Automated Quantitative Intelligence Report**  
> **Generated:** 2026-10-27 14:37:26 | **Project Directory:** `generations/AMD_2025-10-27_2026-10-27_gaussian_m3`

---

## 1. Executive Summary

| Parameter | Configuration / Result |
| :--- | :--- |
| **Ticker Symbol** | `AMD` |
| **Analysis Range** | `2025-10-27` to `2026-10-27` |
| **Total Trading Observations** | `1,700` periods |
| **Asset Profile** | Single stock |
| **Model Framework** | Dirichlet Process Gaussian Mixture Model (DPGMM) |
| **Prior Upper Bound Regimes** | `3` |
| **Weight Concentration Prior (γ)** | `0.001` |
| **Active Regimes Discovered** | **`3` regimes** |
| **Latest Trading Date** | `2026-10-26` |
| **Latest Asset Price** | `$531.47` |
| **Current Identified Regime** | **Regime 0** |

---

## 2. Current Market Outlook & Transition Forecast

As of **2026-10-26**, `AMD` is operating in **Regime 0**.

- **Regime Stability:** There is a **88.18%** probability that the asset remains in **Regime 0** tomorrow.
- **Next-Day State Probability Distribution:**
  - $\rightarrow$ **Regime 0**: `88.18%`
  - $\rightarrow$ **Regime 1**: `11.50%`
  - $\rightarrow$ **Regime 2**: `0.32%`

---

## 3. Market Regime Distribution & Statistical Profiles

| Regime | Trading Days | Frequency (%) | Ann. Return | Ann. Volatility | Sharpe (Rf=0) | Mean Mom (50d) | Yield Spread (10Y-2Y) | Tariff Rate (%) | Regime Characterization |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Regime 0** | 1,245 | 73.2% | +23.22% | 26.70% | 0.87 | +1.53% | 0.51% | 2.72% | Bull Market (High Volatility / Momentum Rally) |
| **Regime 1** | 280 | 16.5% | +405.67% | 156.87% | 2.59 | -2.31% | 0.49% | 2.72% | Bull Market (High Volatility / Momentum Rally) |
| **Regime 2** | 175 | 10.3% | -54.46% | 36.19% | -1.50 | +3.78% | 0.42% | 2.72% | Bear Market (High Volatility / Sharp Correction) |

> Characterization thresholds (single stock): trending when annualized return is beyond **±10%**, high volatility at **25%+** annualized. Figures annualized from 1,764 bars per year.


---

## 4. Empirical Transition Probability Matrix

| Current \ Next | Regime 0 | Regime 1 | Regime 2 |
| :--- | :---: | :---: | :---: |
| **Regime 0** | **88.18%** | 11.50% | 0.32% |
| **Regime 1** | 48.57% | **38.21%** | 13.21% |
| **Regime 2** | 6.29% | 17.14% | **76.57%** |


### Regime Persistence & Expected Dwell Times

| Regime | Persistence P(S|S) | Expected Duration (Days) | Primary Exit Destination | Exit Prob (%) |
| :---: | :---: | :---: | :---: | :---: |
| Regime 0 | 88.18% | 8.5 days | Regime 1 | 11.50% |
| Regime 1 | 38.21% | 1.6 days | Regime 0 | 48.57% |
| Regime 2 | 76.57% | 4.3 days | Regime 1 | 17.14% |


---

## 5. Feature Engineering & Dataset Summary

| Feature | Count | Mean | Std Dev | Min | 25% | Median | 75% | Max |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `log_return` | 1,700 | 0.0004 | 0.0163 | -0.1499 | -0.0048 | -0.0000 | 0.0052 | 0.1461 |
| `volatility` | 1,700 | 0.2304 | 0.1201 | 0.0273 | 0.1464 | 0.2073 | 0.2875 | 0.7155 |
| `momentum_50` | 1,700 | 0.0113 | 0.0618 | -0.1946 | -0.0287 | 0.0083 | 0.0488 | 0.2242 |
| `yield_spread` | 1,700 | 0.4981 | 0.1215 | 0.2000 | 0.4100 | 0.5000 | 0.5800 | 0.7400 |
| `tariff_rate` | 1,700 | 2.7200 | 0.0000 | 2.7200 | 2.7200 | 2.7200 | 2.7200 | 2.7200 |


---

## 6. Current Volatility & Options Breakdown

> **Live snapshot** taken 2026-10-27 14:37 · Spot **$531.28** · Expiries within 45 days · Source: Yahoo Finance option chains

### Key Takeaways

- **Volatility pricing:** Options are **fairly priced** vs. recent movement (IV 60.1% vs. 20d realized 52.7%).
- **Term structure:** **Flat**: no distinct near-term event priced in.
- **Expected move:** ±6.1% by 2026-11-02 ($498.78 – $563.78).
- **Positioning:** Put/call open interest is 1.01 → Defensive (puts dominate). Today's trading put/call volume is 0.68 → Bullish (calls dominate).
- **Skew:** Upside calls are bid over puts (73.1% vs. 62.8% IV): traders are chasing a rally.
- **Where the bets sit:** Call open interest clusters **far above spot** and put open interest clusters **far below spot**. Large far-from-spot clusters usually reflect hedges and lottery-ticket bets rather than an expected move.
- **Near-term levels (2026-10-30, largest short-dated expiry):** heavy put interest at **$450.00** may act as support and call interest at **$620.00** as resistance.
- **Max pain:** $532.50 (+0.2% above spot). Prices sometimes drift toward this level into expiry.

### 6.1 Volatility Snapshot

| Measure | Value | What It Means |
| :--- | :---: | :--- |
| Realized volatility (10d) | 67.6% | How much the stock actually moved over the last 10 trading days (annualized) |
| Realized volatility (20d) | 52.7% | How much the stock actually moved over the last 20 trading days (annualized) |
| Realized volatility (60d) | 57.4% | How much the stock actually moved over the last 60 trading days (annualized) |
| Front-week ATM implied vol (2026-11-02, 6d) | 63.0% | Movement priced into the nearest expiry |
| ~30-day ATM implied vol (2026-11-27, 31d) | 60.1% | Movement priced in over the next month |
| Implied / realized (20d) | 1.14x | Options are **fairly priced** vs. recent movement |
| Term structure (front − 30d) | +2.8% | **Flat**: no distinct near-term event priced in |
| Expected move by 2026-11-02 | ±$32.50 (±6.1%) | ATM straddle implies a range of **$498.78 – $563.78** |


### 6.2 Positioning by Strike Bucket

Open interest (contracts outstanding) and today's volume, grouped by how far the strike sits from the current price (expiries within 45 days).

| Strike Bucket | Strike Range | Call OI | Put OI | Put/Call (OI) | Call Volume | Put Volume | Avg IV (OI-weighted) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Far below spot** | < $478 | 56,523 | 247,878 | 4.39 | 1,951 | 29,629 | 148.5% |
| **Below spot** | $478 – $515 | 14,338 | 54,346 | 3.79 | 6,397 | 26,875 | 68.0% |
| **Near the money** | $515 – $547 | 46,731 | 33,144 | 0.71 | 35,181 | 19,484 | 71.3% |
| **Above spot** | $547 – $584 | 46,323 | 30,400 | 0.66 | 38,826 | 3,836 | 65.4% |
| **Far above spot** | > $584 | 219,072 | 22,897 | 0.10 | 39,028 | 2,599 | 96.1% |
| **All strikes** | | **382,987** | **388,665** | **1.01** | **121,383** | **82,423** | |


### 6.3 Short-Dated Options (< 7 Days)

![AMD Short-Dated Options](options.png)

| Expiry | Days | Call OI | Put OI | Put/Call | Call Wall (top call OI, ±20%) | Put Wall (top put OI, ±20%) | Max Pain |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2026-10-28 | 1 | 20,996 | 17,509 | 0.83 | $600.00 | $480.00 | $527.50 |
| 2026-10-30 | 3 | 102,296 | 106,524 | 1.04 | $620.00 | $450.00 | $532.50 |
| 2026-11-02 | 6 | 4,869 | 6,318 | 1.30 | $550.00 | $430.00 | $532.50 |



---

## 7. Visualizations & Model Artifacts

![AMD Market Regimes](plot.png)

### Artifact Inventory

| Artifact Description | Path |
| :--- | :--- |
| **Markdown Analysis Report** | `generations/AMD_2025-10-27_2026-10-27_gaussian_m3/report.md` |
| **Fitted Model & Scaler Bundle** | `generations/AMD_2025-10-27_2026-10-27_gaussian_m3/model.joblib` |
| **Labeled Feature Dataset** | `generations/AMD_2025-10-27_2026-10-27_gaussian_m3/labeled.csv` |
| **Regime Price Visualization** | `generations/AMD_2025-10-27_2026-10-27_gaussian_m3/plot.png` |
| **Short-Dated Options Visualization** | `generations/AMD_2025-10-27_2026-10-27_gaussian_m3/options.png` |

---
*Report produced by Dirichlet Process Regime Engine.*
