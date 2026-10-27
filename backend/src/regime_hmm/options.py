"""
Options & Volatility Analysis.
Pulls live option chains from Yahoo Finance, compares implied vs realized volatility,
summarizes positioning in strike buckets, and plots short-dated (< 7 day) open interest.
"""

import os
from datetime import date, datetime
from typing import Optional
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.regime_hmm.visualiser import BG_COLOR, TEXT_COLOR, GRID_COLOR, PRICE_COLOR

OPTIONS_PLOT_FILENAME = "options.png"
SHORT_DATED_DAYS = 7      # "Short-dated" = expiring in fewer than this many calendar days
MAX_DTE = 45              # Expiries considered for positioning and term structure
WALL_BAND = 0.20          # Call/put walls only consider strikes within this distance of spot
CALL_COLOR = "#00FFA3"
PUT_COLOR = "#FF2E63"

# Strike buckets relative to spot: (label, lower bound, upper bound) as strike/spot - 1
MONEYNESS_BUCKETS = [
    ("Far below spot", -np.inf, -0.10),
    ("Below spot", -0.10, -0.03),
    ("Near the money", -0.03, 0.03),
    ("Above spot", 0.03, 0.10),
    ("Far above spot", 0.10, np.inf),
]

# --- Data ---------------------------------------------------------------------

def load_option_chains(ticker: str, max_dte: int = MAX_DTE) -> tuple[float, pd.DataFrame]:
    """Returns (spot, chains) where chains holds every call/put for expiries within max_dte days."""
    tk = yf.Ticker(ticker)
    expiries = tk.options
    if not expiries:
        raise ValueError(f"No listed options found for {ticker}")

    today = date.today()
    frames = []
    spot = None
    for exp in expiries:
        dte = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days
        if dte < 0:
            continue
        if dte > max_dte and frames:
            break
        chain = tk.option_chain(exp)
        if spot is None and getattr(chain, "underlying", None):
            spot = chain.underlying.get("regularMarketPrice")
        for kind, df in (("call", chain.calls), ("put", chain.puts)):
            df = df[["strike", "volume", "openInterest", "impliedVolatility", "bid", "ask", "lastPrice"]].copy()
            df["type"] = kind
            df["expiry"] = exp
            df["dte"] = dte
            frames.append(df)

    if spot is None:
        spot = float(tk.fast_info["lastPrice"])

    chains = pd.concat(frames, ignore_index=True)
    chains[["volume", "openInterest"]] = chains[["volume", "openInterest"]].fillna(0)
    # Yahoo reports placeholder IVs near zero for illiquid strikes; exclude them from IV stats
    chains.loc[(chains["impliedVolatility"] < 0.01) | (chains["impliedVolatility"] > 5), "impliedVolatility"] = np.nan
    chains["moneyness"] = chains["strike"] / spot - 1
    return float(spot), chains

def realized_volatility(price_df: pd.DataFrame, windows=(10, 20, 60)) -> dict[int, float]:
    """Annualized close-to-close volatility from daily closes (resampled if intraday)."""
    daily_close = price_df["Close"].squeeze().resample("1D").last().dropna()
    log_ret = np.log(daily_close / daily_close.shift(1)).dropna()
    return {w: float(log_ret.tail(w).std() * np.sqrt(252)) for w in windows if len(log_ret) >= w}

# --- Metrics ------------------------------------------------------------------

def _mid(row: pd.Series) -> float:
    if row["bid"] > 0 and row["ask"] > 0:
        return (row["bid"] + row["ask"]) / 2
    return row["lastPrice"]

def _atm_strike(exp_chain: pd.DataFrame, spot: float) -> float:
    strikes = exp_chain["strike"].unique()
    return float(strikes[np.argmin(np.abs(strikes - spot))])

def atm_iv(exp_chain: pd.DataFrame, spot: float) -> float:
    atm = exp_chain[exp_chain["strike"] == _atm_strike(exp_chain, spot)]
    return float(atm["impliedVolatility"].mean())

def straddle_move(exp_chain: pd.DataFrame, spot: float) -> Optional[float]:
    """ATM straddle mid price: the market's priced-in move by expiry."""
    atm = exp_chain[exp_chain["strike"] == _atm_strike(exp_chain, spot)]
    call, put = atm[atm["type"] == "call"], atm[atm["type"] == "put"]
    if call.empty or put.empty:
        return None
    return float(_mid(call.iloc[0]) + _mid(put.iloc[0]))

def max_pain(exp_chain: pd.DataFrame) -> float:
    """Strike at which the total intrinsic value paid to option holders is smallest."""
    strikes = np.sort(exp_chain["strike"].unique())
    calls = exp_chain[exp_chain["type"] == "call"]
    puts = exp_chain[exp_chain["type"] == "put"]
    payout = [
        (calls["openInterest"] * np.maximum(k - calls["strike"], 0)).sum()
        + (puts["openInterest"] * np.maximum(puts["strike"] - k, 0)).sum()
        for k in strikes
    ]
    return float(strikes[int(np.argmin(payout))])

def _quantity(df: pd.DataFrame) -> tuple[pd.Series, str]:
    """Open interest is the quantity outstanding; fall back to volume when OI isn't published yet."""
    if df["openInterest"].sum() > 0:
        return df["openInterest"], "OI"
    return df["volume"], "Vol"

def _ratio(num: float, den: float) -> float:
    return num / den if den > 0 else np.nan

def _weighted_quantiles(values: np.ndarray, weights: np.ndarray, qs) -> np.ndarray:
    order = np.argsort(values)
    values, weights = values[order], weights[order]
    cum = (np.cumsum(weights) - 0.5 * weights) / weights.sum()
    return np.interp(qs, cum, values)

# --- Plot ---------------------------------------------------------------------

def plot_short_dated_options(chains: pd.DataFrame, spot: float, ticker: str, save_path: str) -> bool:
    """Box plot of strikes weighted by open interest, calls vs puts, for each expiry < 7 days."""
    short = chains[chains["dte"] < SHORT_DATED_DAYS]
    expiries = sorted(short["expiry"].unique())
    if not expiries:
        return False

    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    rng = np.random.default_rng(42)
    offset, width = 0.2, 0.32
    all_lo, all_hi, max_q = [], [], 1.0
    for exp in expiries:
        for kind in ("call", "put"):
            q, _ = _quantity(short[(short["expiry"] == exp) & (short["type"] == kind)])
            max_q = max(max_q, float(q.max()) if len(q) else 0.0)

    for i, exp in enumerate(expiries):
        for kind, color, dx in (("call", CALL_COLOR, -offset), ("put", PUT_COLOR, offset)):
            df = short[(short["expiry"] == exp) & (short["type"] == kind)]
            qty, qty_label = _quantity(df)
            mask = qty > 0
            if not mask.any():
                continue
            strikes, weights = df["strike"][mask].to_numpy(), qty[mask].to_numpy(dtype=float)
            p5, q1, med, q3, p95 = _weighted_quantiles(strikes, weights, [0.05, 0.25, 0.5, 0.75, 0.95])
            all_lo.append(p5)
            all_hi.append(p95)

            box = ax.bxp(
                [{"med": med, "q1": q1, "q3": q3, "whislo": p5, "whishi": p95, "fliers": []}],
                positions=[i + dx], widths=width, patch_artist=True, showfliers=False,
                boxprops=dict(facecolor=color + "40", edgecolor=color, linewidth=1.8),
                medianprops=dict(color=color, linewidth=3),
                whiskerprops=dict(color=color, linewidth=1.4),
                capprops=dict(color=color, linewidth=1.4),
                manage_ticks=False,
            )
            for patch in box["boxes"]:
                patch.set_zorder(2)

            # Each meaningful strike as a bubble sized by its quantity (tiny positions hidden to reduce noise)
            shown = weights >= 0.02 * weights.max()
            jitter = rng.uniform(-width / 4, width / 4, size=shown.sum())
            ax.scatter(
                i + dx + jitter, strikes[shown], s=10 + 700 * weights[shown] / max_q,
                color=color, alpha=0.45, edgecolors=BG_COLOR, linewidths=0.5, zorder=3,
            )
            ax.annotate(
                f"{weights.sum():,.0f} {qty_label}", (i + dx, p95), xytext=(0, 10),
                textcoords="offset points", ha="center", color=color, fontsize=9, fontweight="bold", zorder=5,
                bbox=dict(boxstyle="round,pad=0.25", facecolor=BG_COLOR, edgecolor=color, alpha=0.9),
            )

    ax.axhline(spot, color=PRICE_COLOR, linestyle="--", linewidth=1.2, alpha=0.8, zorder=1)
    ax.annotate(f"Spot ${spot:,.2f}", (1.0, spot), xycoords=("axes fraction", "data"), xytext=(-4, 4),
                textcoords="offset points", ha="right", color=PRICE_COLOR, fontsize=10,
                bbox=dict(boxstyle="round,pad=0.25", facecolor=BG_COLOR, edgecolor=GRID_COLOR, alpha=0.9))

    # Focus on where the quantity sits; far-out strikes would otherwise flatten the boxes
    lo, hi = min(all_lo + [spot]), max(all_hi + [spot])
    pad = (hi - lo) * 0.12 or spot * 0.05
    ax.set_ylim(lo - pad, hi + pad)

    labels = [f"{datetime.strptime(e, '%Y-%m-%d'):%b %d}\n({short.loc[short['expiry'] == e, 'dte'].iloc[0]}d)" for e in expiries]
    ax.set_xticks(range(len(expiries)), labels)
    ax.set_xlim(-0.7, len(expiries) - 0.3)

    ax.set_title(f"{ticker} Short-Dated Options (< {SHORT_DATED_DAYS} Days): Strike Distribution by Open Interest",
                 fontsize=15, fontweight="bold", color=TEXT_COLOR)
    ax.set_ylabel("Strike Price", fontsize=12, color=TEXT_COLOR)
    ax.set_xlabel("Expiry (days to expiry)", fontsize=12, color=TEXT_COLOR)
    ax.tick_params(colors=TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    ax.grid(True, axis="y", color=GRID_COLOR, alpha=0.6, linestyle="--")

    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=CALL_COLOR + "40", edgecolor=CALL_COLOR, label="Calls"),
        plt.Rectangle((0, 0), 1, 1, facecolor=PUT_COLOR + "40", edgecolor=PUT_COLOR, label="Puts"),
        plt.Line2D([0], [0], color=PRICE_COLOR, linestyle="--", label="Spot"),
    ]
    legend = ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1, 1), facecolor=BG_COLOR, edgecolor=GRID_COLOR)
    for text in legend.get_texts():
        text.set_color(TEXT_COLOR)
    fig.text(0.01, 0.01, "Box = 25th–75th percentile of quantity, line = median strike, whiskers = 5th–95th. Bubble size = quantity at that strike.",
             color=TEXT_COLOR, alpha=0.7, fontsize=9)

    plt.tight_layout(rect=(0, 0.03, 1, 1))
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    plt.savefig(save_path, dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Options visualization saved to {save_path}")
    return True

# --- Markdown -----------------------------------------------------------------

def _pct(x: float, signed: bool = False) -> str:
    if x is None or pd.isna(x):
        return "N/A"
    return f"{x * 100:+.1f}%" if signed else f"{x * 100:.1f}%"

def _num(x: float) -> str:
    return "N/A" if x is None or pd.isna(x) else f"{x:,.0f}"

def _pc(x: float) -> str:
    return "N/A" if pd.isna(x) else f"{x:.2f}"

def _sentiment(pc: float) -> str:
    if pd.isna(pc):
        return "No read"
    if pc > 1.0:
        return "Defensive (puts dominate)"
    if pc < 0.7:
        return "Bullish (calls dominate)"
    return "Balanced"

def format_volatility_table_md(rv: dict, front: Optional[dict], month: Optional[dict], spot: float) -> tuple[str, list[str]]:
    lines = ["| Measure | Value | What It Means |", "| :--- | :---: | :--- |"]
    takeaways = []
    for w, v in rv.items():
        lines.append(f"| Realized volatility ({w}d) | {_pct(v)} | How much the stock actually moved over the last {w} trading days (annualized) |")

    rv20 = rv.get(20)
    if front:
        lines.append(f"| Front-week ATM implied vol ({front['expiry']}, {front['dte']}d) | {_pct(front['iv'])} | Movement priced into the nearest expiry |")
    if month:
        lines.append(f"| ~30-day ATM implied vol ({month['expiry']}, {month['dte']}d) | {_pct(month['iv'])} | Movement priced in over the next month |")

    ref = month or front
    if ref and rv20 and not pd.isna(ref["iv"]):
        ratio = ref["iv"] / rv20
        if ratio > 1.2:
            read = "Options are **expensive** vs. recent movement: the market expects more volatility ahead"
        elif ratio < 0.8:
            read = "Options are **cheap** vs. recent movement: the market expects things to calm down"
        else:
            read = "Options are **fairly priced** vs. recent movement"
        lines.append(f"| Implied / realized (20d) | {ratio:.2f}x | {read} |")
        takeaways.append(f"**Volatility pricing:** {read} (IV {_pct(ref['iv'])} vs. 20d realized {_pct(rv20)}).")

    if front and month and front["expiry"] != month["expiry"] and not pd.isna(front["iv"]) and not pd.isna(month["iv"]):
        spread = front["iv"] - month["iv"]
        if spread > 0.03:
            read = "**Inverted**: near-term stress or an upcoming event (e.g. earnings) is priced in"
        elif spread < -0.03:
            read = "**Upward sloping**: calm near term, normal uncertainty further out"
        else:
            read = "**Flat**: no distinct near-term event priced in"
        lines.append(f"| Term structure (front − 30d) | {_pct(spread, signed=True)} | {read} |")
        takeaways.append(f"**Term structure:** {read}.")

    if front and front.get("move"):
        move = front["move"]
        lines.append(
            f"| Expected move by {front['expiry']} | ±${move:,.2f} (±{move / spot * 100:.1f}%) | "
            f"ATM straddle implies a range of **${spot - move:,.2f} – ${spot + move:,.2f}** |"
        )
        takeaways.append(f"**Expected move:** ±{move / spot * 100:.1f}% by {front['expiry']} (${spot - move:,.2f} – ${spot + move:,.2f}).")

    return "\n".join(lines) + "\n", takeaways

def format_moneyness_table_md(chains: pd.DataFrame, spot: float) -> tuple[str, list[str]]:
    lines = [
        "| Strike Bucket | Strike Range | Call OI | Put OI | Put/Call (OI) | Call Volume | Put Volume | Avg IV (OI-weighted) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    stats = {}
    for label, lo, hi in MONEYNESS_BUCKETS:
        b = chains[(chains["moneyness"] >= lo) & (chains["moneyness"] < hi)]
        calls, puts = b[b["type"] == "call"], b[b["type"] == "put"]
        iv_rows = b.dropna(subset=["impliedVolatility"])
        iv = np.average(iv_rows["impliedVolatility"], weights=iv_rows["openInterest"]) if iv_rows["openInterest"].sum() > 0 else iv_rows["impliedVolatility"].mean()
        if np.isinf(lo):
            strike_range = f"< ${spot * (1 + hi):,.0f}"
        elif np.isinf(hi):
            strike_range = f"> ${spot * (1 + lo):,.0f}"
        else:
            strike_range = f"${spot * (1 + lo):,.0f} – ${spot * (1 + hi):,.0f}"
        stats[label] = {
            "call_iv": calls["impliedVolatility"].mean(), "put_iv": puts["impliedVolatility"].mean(),
            "call_oi": calls["openInterest"].sum(), "put_oi": puts["openInterest"].sum(),
        }
        lines.append(
            f"| **{label}** | {strike_range} | {_num(calls['openInterest'].sum())} | {_num(puts['openInterest'].sum())} | "
            f"{_pc(_ratio(puts['openInterest'].sum(), calls['openInterest'].sum()))} | {_num(calls['volume'].sum())} | "
            f"{_num(puts['volume'].sum())} | {_pct(iv)} |"
        )

    takeaways = []
    total_call_oi = chains.loc[chains["type"] == "call", "openInterest"].sum()
    total_put_oi = chains.loc[chains["type"] == "put", "openInterest"].sum()
    total_call_vol = chains.loc[chains["type"] == "call", "volume"].sum()
    total_put_vol = chains.loc[chains["type"] == "put", "volume"].sum()
    pc_oi, pc_vol = _ratio(total_put_oi, total_call_oi), _ratio(total_put_vol, total_call_vol)
    lines.append(
        f"| **All strikes** | | **{_num(total_call_oi)}** | **{_num(total_put_oi)}** | **{_pc(pc_oi)}** | "
        f"**{_num(total_call_vol)}** | **{_num(total_put_vol)}** | |"
    )
    takeaways.append(
        f"**Positioning:** Put/call open interest is {_pc(pc_oi)} → {_sentiment(pc_oi)}. "
        f"Today's trading put/call volume is {_pc(pc_vol)} → {_sentiment(pc_vol)}."
    )

    down_iv, up_iv = stats["Below spot"]["put_iv"], stats["Above spot"]["call_iv"]
    if not (pd.isna(down_iv) or pd.isna(up_iv)):
        skew = down_iv - up_iv
        if skew > 0.02:
            read = f"downside protection is priced at a premium (puts {_pct(down_iv)} vs. calls {_pct(up_iv)} IV): traders are paying up to hedge a drop"
        elif skew < -0.02:
            read = f"upside calls are bid over puts ({_pct(up_iv)} vs. {_pct(down_iv)} IV): traders are chasing a rally"
        else:
            read = f"put and call IV are roughly even ({_pct(down_iv)} vs. {_pct(up_iv)}): no strong directional fear or greed"
        takeaways.append(f"**Skew:** {read[0].upper() + read[1:]}.")

    call_hub = max(stats, key=lambda k: stats[k]["call_oi"])
    put_hub = max(stats, key=lambda k: stats[k]["put_oi"])
    takeaways.append(
        f"**Where the bets sit:** Call open interest clusters **{call_hub.lower()}** and put open interest clusters **{put_hub.lower()}**. "
        f"Large far-from-spot clusters usually reflect hedges and lottery-ticket bets rather than an expected move."
    )
    return "\n".join(lines) + "\n", takeaways

def format_short_dated_table_md(chains: pd.DataFrame, spot: float) -> tuple[str, list[str]]:
    short = chains[chains["dte"] < SHORT_DATED_DAYS]
    if short.empty:
        return f"No expiries within the next {SHORT_DATED_DAYS} days.\n", []

    lines = [
        f"| Expiry | Days | Call OI | Put OI | Put/Call | Call Wall (top call OI, ±{WALL_BAND:.0%}) | Put Wall (top put OI, ±{WALL_BAND:.0%}) | Max Pain |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    walls = []
    for exp in sorted(short["expiry"].unique()):
        e = short[short["expiry"] == exp]
        calls, puts = e[e["type"] == "call"], e[e["type"] == "put"]
        # Walls ignore far-away strikes, which tend to be stale hedges rather than live levels
        near = (e["moneyness"].abs() <= WALL_BAND)
        calls_near, puts_near = calls[near[calls.index]], puts[near[puts.index]]
        call_wall = calls_near.loc[calls_near["openInterest"].idxmax(), "strike"] if calls_near["openInterest"].sum() > 0 else np.nan
        put_wall = puts_near.loc[puts_near["openInterest"].idxmax(), "strike"] if puts_near["openInterest"].sum() > 0 else np.nan
        pain = max_pain(e) if e["openInterest"].sum() > 0 else np.nan
        walls.append((exp, call_wall, put_wall, pain))
        fmt = lambda k: "N/A" if pd.isna(k) else f"${k:,.2f}"
        lines.append(
            f"| {exp} | {e['dte'].iloc[0]} | {_num(calls['openInterest'].sum())} | {_num(puts['openInterest'].sum())} | "
            f"{_pc(_ratio(puts['openInterest'].sum(), calls['openInterest'].sum()))} | {fmt(call_wall)} | {fmt(put_wall)} | {fmt(pain)} |"
        )

    takeaways = []
    # The largest short-dated expiry is the one most likely to influence price near term
    biggest = max(walls, key=lambda w: short.loc[short["expiry"] == w[0], "openInterest"].sum())
    exp, call_wall, put_wall, pain = biggest
    if not (pd.isna(call_wall) or pd.isna(put_wall)):
        takeaways.append(
            f"**Near-term levels ({exp}, largest short-dated expiry):** heavy put interest at **${put_wall:,.2f}** "
            f"may act as support and call interest at **${call_wall:,.2f}** as resistance."
        )
    if not pd.isna(pain):
        direction = "above" if pain > spot else "below" if pain < spot else "at"
        takeaways.append(
            f"**Max pain:** ${pain:,.2f} ({(pain / spot - 1) * 100:+.1f}% {direction} spot). Prices sometimes drift toward this level into expiry."
        )
    return "\n".join(lines) + "\n", takeaways

def build_options_section(ticker: str, price_df: pd.DataFrame, out_dir: str, end_date: str, section_number: int = 6) -> tuple[str, bool]:
    """Returns (markdown section, whether the options plot was written)."""
    n = section_number
    header = [f"## {n}. Current Volatility & Options Breakdown", ""]
    try:
        spot, chains = load_option_chains(ticker)
    except Exception as e:
        print(f"⚠️ Skipping options analysis: {e}")
        return "\n".join(header + [f"> Options data unavailable for `{ticker}`: {e}", ""]), False

    rv = realized_volatility(price_df)
    today = date.today().isoformat()

    by_expiry = {exp: g for exp, g in chains.groupby("expiry")}
    # Front reference: the furthest expiry inside the short-dated window (about a week out).
    # 0DTE is excluded because its IV is too noisy to read.
    front_candidates = [e for e in sorted(by_expiry) if 1 <= by_expiry[e]["dte"].iloc[0] < SHORT_DATED_DAYS]
    front = month = None
    if front_candidates:
        exp = front_candidates[-1]
        front = {
            "expiry": exp, "dte": int(by_expiry[exp]["dte"].iloc[0]),
            "iv": atm_iv(by_expiry[exp], spot), "move": straddle_move(by_expiry[exp], spot),
        }
    month_exp = min(by_expiry, key=lambda e: abs(by_expiry[e]["dte"].iloc[0] - 30))
    if by_expiry[month_exp]["dte"].iloc[0] >= 14:
        month = {"expiry": month_exp, "dte": int(by_expiry[month_exp]["dte"].iloc[0]), "iv": atm_iv(by_expiry[month_exp], spot)}

    vol_md, vol_takeaways = format_volatility_table_md(rv, front, month, spot)
    money_md, money_takeaways = format_moneyness_table_md(chains, spot)
    short_md, short_takeaways = format_short_dated_table_md(chains, spot)

    plot_path = os.path.join(out_dir, OPTIONS_PLOT_FILENAME)
    has_plot = plot_short_dated_options(chains, spot, ticker, plot_path)

    note = f"> **Live snapshot** taken {datetime.now():%Y-%m-%d %H:%M} · Spot **${spot:,.2f}** · Expiries within {MAX_DTE} days · Source: Yahoo Finance option chains"
    if end_date < today:
        note += f"  \n> Note: the regime analysis ends on `{end_date}`, but options data is always current."

    parts = header + [
        note, "",
        "### Key Takeaways", "",
        *[f"- {t}" for t in vol_takeaways + money_takeaways + short_takeaways], "",
        f"### {n}.1 Volatility Snapshot", "", vol_md, "",
        f"### {n}.2 Positioning by Strike Bucket", "",
        f"Open interest (contracts outstanding) and today's volume, grouped by how far the strike sits from the current price "
        f"(expiries within {MAX_DTE} days).", "",
        money_md, "",
        f"### {n}.3 Short-Dated Options (< {SHORT_DATED_DAYS} Days)", "",
    ]
    if has_plot:
        parts += [f"![{ticker} Short-Dated Options]({OPTIONS_PLOT_FILENAME})", ""]
    parts += [short_md, ""]
    return "\n".join(parts), has_plot
