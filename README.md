# Regime HMM Financial Model

Author: Keegan Coskey

## Overview

This quantitative finance project implements a Dirichlet Process Gaussian Mixture Model (DPGMM) to dynamically identify hidden market regimes (bull, bear, consolidation, high-volatility) using a blend of daily price action, fundamental corporate data, and global macroeconomic indicators.

## Project Structure

```
DPGMM_interface/
  .venv/                 Python virtual environment (shared by the backend)
  backend/
    main.py              CLI entrypoint
    api/app.py           FastAPI app (dev only, no auth)
    api/store.py         Generation store: caching, history, legacy import
    src/regime_hmm/      Data loading, features, models, plotting, report writer, pipeline
    data/                Raw price cache and processed datasets
    generations/<id>/    One folder per run: report.md, plot.png, meta.json, model.joblib, labeled.csv
    .env                 FMP_API_KEY, FRED_API_KEY
  frontend/              Vite + React + TypeScript UI
```

A generation id is `TICKER_START_END_{gaussian|fat}_m{max_regimes}`. Requesting the same id again returns the stored result instead of re-running the model.

## Running (dev)

Backend (from `backend/`):

```
../.venv/bin/pip install -r requirements.txt
../.venv/bin/uvicorn api.app:app --reload --port 8000
```

Frontend (from `frontend/`):

```
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the backend on port 8000.

- **Generate**: enter a ticker, date range (within the last 729 days, Yahoo's 1h data limit), max regimes and optional fat-tail model. The regime plot is shown first, followed by the report.
- **Generated**: every previous run, filterable by ticker.

Each report includes a **Current Volatility & Options Breakdown** section built from a live Yahoo Finance option-chain snapshot (expiries within 45 days): realized vs. implied volatility, term structure, the straddle-implied expected move, put/call positioning in strike buckets, and a box plot of open interest by strike for expiries under 7 days. Because the options data is live, it reflects the time of generation, not the analysis end date.

CLI (from `backend/`), which writes to the same store:

```
../.venv/bin/python main.py -t AMD -m 3 -s 2025-01-02 -e 2026-10-23 [--fat_tail]
```

### API

| Method | Path | Description |
| :--- | :--- | :--- |
| GET | `/api/health` | Health check |
| GET | `/api/palette` | Regime color palette (indexed by regime id) |
| POST | `/api/generate` | `{ticker, start_date, end_date, max_regimes, fat_tail}`; returns `{meta, markdown, cached}` |
| GET | `/api/generations` | All generation metadata, newest first |
| GET | `/api/generations/{id}` | `{meta, markdown}` |
| GET | `/api/generations/{id}/plot.png` | Regime plot |
| GET | `/api/generations/{id}/options.png` | Short-dated options box plot |

## Assumptions

Stationarity: The DPGMM assumes feature stationarity. Absolute prices and raw CAPEX are transformed into log returns, moving average distances, and percentage growth rates to prevent the model from clustering purely based on time drift.
Gaussian Distributions: Features within a single regime are assumed to follow a multivariate Gaussian distribution.
Look-Ahead Bias: To prevent data leakage, mixed-frequency macro indicators (World Bank tariffs, FRED yields, FMP CAPEX) are strictly forward-filled (ffill) onto a daily trading calendar.
Data Limits: The model assumes Yahoo Finance's 730-day historical limit for hourly (1h) interval data.

## Notes on Implementation

Dynamic Regime Spawning: By leveraging a Dirichlet Process prior, the architecture eliminates the need to hardcode a fixed number of market states. It mathematically determines the optimal active clusters by penalizing complexity.
Directional Momentum: A 50-day moving average distance feature is included to explicitly force the model to separate upward grinding bull markets from downward grinding bear markets that share identical volatility profiles.
Development Environment: The pipeline is structured for WSL/Linux environments running Python virtual environments, utilizing a standard src/ package layout to isolate data extraction from model logic.
Future Improvements
Data Engineering: Migrate the local CSV caching layer to a relational database (e.g., PostgreSQL) utilizing Flyway for schema migrations to robustly manage growing time-series datasets.
Containerization: Package the pipeline into a Docker container to ensure isolated execution environments and simplify deployment.
Covariance Stability: Implement Cholesky decomposition or advanced regularization techniques to prevent covariance matrix singularities when macro features become too highly correlated.
Version Control & CI/CD: Establish a GitLab CI/CD pipeline to automate model retraining and backtesting against new market data.
