"""Load candle data from CSV files.

Expected columns:
timestamp, symbol, open, high, low, close, volume
"""

from pathlib import Path

import pandas as pd
import yaml


REQUIRED_COLUMNS = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]


def load_candles(csv_path: str | Path) -> pd.DataFrame:
    """Load candles and validate the basic schema."""
    candles = pd.read_csv(csv_path, parse_dates=["timestamp"])
    missing = set(REQUIRED_COLUMNS) - set(candles.columns)
    if missing:
        raise ValueError(f"Missing required candle columns: {sorted(missing)}")

    return candles.sort_values(["timestamp", "symbol"]).reset_index(drop=True)


def load_settings(settings_path: str | Path) -> dict:
    """Load project settings from YAML."""
    with Path(settings_path).open("r", encoding="utf-8") as settings_file:
        return yaml.safe_load(settings_file) or {}


def add_trading_day(candles: pd.DataFrame) -> pd.DataFrame:
    """Add a calendar trading_day column used by market structure helpers."""
    enriched = candles.copy()
    enriched["trading_day"] = enriched["timestamp"].dt.date
    return enriched


def add_midnight_open(candles: pd.DataFrame) -> pd.DataFrame:
    """Add each symbol's midnight open for every trading day."""
    enriched = add_trading_day(candles)
    midnight_rows = enriched[enriched["timestamp"].dt.time.astype(str) == "00:00:00"]
    midnight_opens = midnight_rows[["symbol", "trading_day", "open"]].rename(
        columns={"open": "midnight_open"}
    )
    return enriched.merge(midnight_opens, on=["symbol", "trading_day"], how="left")


def add_previous_day_levels(candles: pd.DataFrame) -> pd.DataFrame:
    """Add previous day high and low columns for each symbol."""
    enriched = add_trading_day(candles)
    daily_levels = (
        enriched.groupby(["symbol", "trading_day"], as_index=False)
        .agg(day_high=("high", "max"), day_low=("low", "min"))
        .sort_values(["symbol", "trading_day"])
    )
    daily_levels["pdh"] = daily_levels.groupby("symbol")["day_high"].shift(1)
    daily_levels["pdl"] = daily_levels.groupby("symbol")["day_low"].shift(1)
    previous_levels = daily_levels[["symbol", "trading_day", "pdh", "pdl"]]
    return enriched.merge(previous_levels, on=["symbol", "trading_day"], how="left")


def enrich_market_structure(candles: pd.DataFrame) -> pd.DataFrame:
    """Add reusable market structure columns to a candle DataFrame."""
    enriched = add_midnight_open(candles)
    enriched = add_previous_day_levels(enriched)
    return enriched
