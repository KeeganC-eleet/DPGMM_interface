import sys
import argparse
from datetime import datetime
from api import store

def main(max_regimes: int = None, ticker: str = None, start_date: str = None, end_date: str = None):
    # Allow customizable max_regimes, ticker, and model choice via CLI
    if max_regimes is None or ticker is None:
        positional = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
        cli_max_regimes = None
        cli_ticker = None
        
        if len(positional) >= 1:
            try:
                cli_max_regimes = int(positional[0])
                if len(positional) >= 2:
                    cli_ticker = positional[1].strip("'\"")
            except ValueError:
                cli_ticker = positional[0].strip("'\"")
                if len(positional) >= 2:
                    try:
                        cli_max_regimes = int(positional[1])
                    except ValueError:
                        pass
        
        parser = argparse.ArgumentParser(description="Market Regime Detection using DPGMM")
        parser.add_argument("--ticker", "-t", type=str, default=None, help="Stock ticker symbol")
        parser.add_argument("--max_regimes", "-m", type=int, default=None, help="Max regimes")
        # NEW: Flag to toggle the PyMC Fat-Tailed Model
        parser.add_argument("--fat_tail", "-f", action="store_true", help="Use PyMC Student's t-Mixture Model")
        parser.add_argument("--start", "-s", type=str, default=None, help="Start date (YYYY-MM-DD)")
        parser.add_argument("--end", "-e", type=str, default=None, help="End date (YYYY-MM-DD)")
        
        flag_args, _ = parser.parse_known_args()
        
        if max_regimes is None:
            max_regimes = flag_args.max_regimes if flag_args.max_regimes is not None else (cli_max_regimes if cli_max_regimes is not None else 3)
        if ticker is None:
            ticker = flag_args.ticker if flag_args.ticker is not None else (cli_ticker if cli_ticker is not None else "AAPL")
        use_fat_tail = flag_args.fat_tail
        flag_start, flag_end = flag_args.start, flag_args.end
    else:
        use_fat_tail = False
        flag_start = flag_end = None

    # --- Configuration ---
    if start_date is None:
        start_date = flag_start or "2024-11-01"
    if end_date is None:
        end_date = flag_end or datetime.today().strftime('%Y-%m-%d')

    # Runs through the generation store so CLI runs show up in the frontend and reuse cached results
    generation, cached = store.generate(
        ticker=ticker.upper(),
        start_date=start_date,
        end_date=end_date,
        max_regimes=max_regimes,
        fat_tail=use_fat_tail,
    )
    status = "Loaded cached generation" if cached else "Generated"
    print(f"{status}: {store.GENERATIONS_DIR / generation['meta']['id']}")
    
if __name__ == "__main__":
    main()