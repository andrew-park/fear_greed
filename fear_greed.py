#!/usr/bin/env python3
"""Transparent, price-based fear/greed proxies for the S&P 500 and KOSPI."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import yfinance as yf


@dataclass(frozen=True)
class Market:
    name: str
    ticker: str


MARKETS = {
    "sp500": Market("S&P 500", "^GSPC"),
    "kospi": Market("KOSPI", "^KS11"),
}

SCORE_COLUMNS = {
    "trend_score": "125-day trend",
    "momentum_score": "20-day momentum",
    "range_score": "52-week range position",
    "drawdown_score": "252-day drawdown",
    "volatility_score": "20-day realized volatility",
}


def sentiment_label(score: float) -> str:
    """Map a 0–100 score to conventional five-band sentiment wording."""
    if score <= 25:
        return "Extreme Fear"
    if score <= 45:
        return "Fear"
    if score <= 55:
        return "Neutral"
    if score <= 75:
        return "Greed"
    return "Extreme Greed"


def _rolling_percentile(series: pd.Series, lookback: int, min_periods: int) -> pd.Series:
    """Percentile rank of each observation within its trailing history."""
    return series.rolling(lookback, min_periods=min_periods).rank(pct=True) * 100.0


def calculate_fear_greed(
    close: pd.Series,
    lookback: int = 756,
    min_history: int = 252,
) -> pd.DataFrame:
    """Calculate a 0–100 composite and its five price-action components.

    Higher values indicate greedier/stronger market conditions. Scores are
    rolling historical percentiles, not the CNN index's proprietary values.
    """
    prices = pd.to_numeric(close, errors="coerce").dropna().sort_index()
    if prices.empty:
        raise ValueError("No valid closing prices were supplied.")
    if (prices <= 0).any():
        raise ValueError("Closing prices must be positive.")
    if lookback < min_history or min_history < 20:
        raise ValueError("lookback must be >= min_history, and min_history must be >= 20.")

    daily_return = prices.pct_change()
    trend_gap = prices / prices.rolling(125, min_periods=125).mean() - 1.0
    momentum_20d = prices.pct_change(20)
    high_252d = prices.rolling(252, min_periods=252).max()
    low_252d = prices.rolling(252, min_periods=252).min()
    range_position = (prices - low_252d) / (high_252d - low_252d).replace(0, float("nan")) * 100.0
    drawdown = prices / high_252d - 1.0
    realized_vol = daily_return.rolling(20, min_periods=20).std() * math.sqrt(252)

    min_rank_samples = min(min_history, lookback)
    components = pd.DataFrame(index=prices.index)
    components["trend_gap"] = trend_gap
    components["momentum_20d"] = momentum_20d
    components["range_position_52w"] = range_position
    components["drawdown_252d"] = drawdown
    components["realized_vol_20d"] = realized_vol

    components["trend_score"] = _rolling_percentile(trend_gap, lookback, min_rank_samples)
    components["momentum_score"] = _rolling_percentile(momentum_20d, lookback, min_rank_samples)
    components["range_score"] = range_position.clip(0, 100)
    # A drawdown closer to zero is stronger, so its percentile is not inverted.
    components["drawdown_score"] = _rolling_percentile(drawdown, lookback, min_rank_samples)
    # Higher realized volatility indicates more fear, so invert its percentile.
    components["volatility_score"] = 100.0 - _rolling_percentile(realized_vol, lookback, min_rank_samples)

    score_cols = list(SCORE_COLUMNS)
    components["fear_greed"] = components[score_cols].mean(axis=1, skipna=False).clip(0, 100)
    return components


def download_close(ticker: str, period: str = "10y") -> pd.Series:
    """Download daily adjusted close history from Yahoo Finance via yfinance."""
    history = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)
    if history.empty or "Close" not in history:
        raise RuntimeError(f"No daily close data returned for {ticker!r}. Check the ticker or try again later.")
    close = history["Close"].dropna()
    if close.empty:
        raise RuntimeError(f"No valid closing prices returned for {ticker!r}.")
    return close


def latest_result(name: str, ticker: str, data: pd.DataFrame) -> dict:
    valid = data.dropna(subset=["fear_greed"])
    if valid.empty:
        raise RuntimeError(
            f"Not enough history to score {name}. Download at least about two years of daily data."
        )
    row = valid.iloc[-1]
    components = {}
    raw_for_score = {
        "trend_score": "trend_gap",
        "momentum_score": "momentum_20d",
        "range_score": "range_position_52w",
        "drawdown_score": "drawdown_252d",
        "volatility_score": "realized_vol_20d",
    }
    for score_col, label in SCORE_COLUMNS.items():
        raw_col = raw_for_score[score_col]
        components[label] = {
            "score": round(float(row[score_col]), 2),
            "raw_value": round(float(row[raw_col]), 6),
        }
    score = float(row["fear_greed"])
    date = pd.Timestamp(valid.index[-1]).strftime("%Y-%m-%d")
    return {
        "market": name,
        "ticker": ticker,
        "date": date,
        "fear_greed": round(score, 2),
        "sentiment": sentiment_label(score),
        "components": components,
    }


def run(markets: Iterable[str], period: str, lookback: int, output: Path | None) -> list[dict]:
    results = []
    csv_frames = []
    for key in markets:
        market = MARKETS[key]
        close = download_close(market.ticker, period=period)
        data = calculate_fear_greed(close, lookback=lookback)
        result = latest_result(market.name, market.ticker, data)
        results.append(result)
        export = data.copy()
        export.insert(0, "close", close.reindex(data.index))
        export.insert(0, "ticker", market.ticker)
        export.insert(0, "market", market.name)
        csv_frames.append(export)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        pd.concat(csv_frames).to_csv(output, index_label="date")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate transparent 0–100 S&P 500 and KOSPI fear/greed proxy scores."
    )
    parser.add_argument(
        "--markets",
        nargs="+",
        choices=sorted(MARKETS),
        default=list(MARKETS),
        help="Markets to calculate (default: both).",
    )
    parser.add_argument("--period", default="10y", help="Yahoo Finance history period, e.g. 5y or 10y (default: 10y).")
    parser.add_argument("--lookback", type=int, default=756, help="Trading-day history window for percentiles (default: 756, about 3 years).")
    parser.add_argument("--output", type=Path, help="Optional path to save all calculated daily values as CSV.")
    args = parser.parse_args()

    try:
        results = run(args.markets, args.period, args.lookback, args.output)
    except (RuntimeError, ValueError, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")

    print(json.dumps(results, ensure_ascii=False, indent=2))
    if args.output:
        print(f"\nSaved daily history to: {args.output}")


if __name__ == "__main__":
    main()
