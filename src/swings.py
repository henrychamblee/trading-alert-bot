"""Swing high and swing low detection.

The current implementation uses a simple lookback/lookforward window. Later,
this can be replaced with stricter market structure rules.
"""

import pandas as pd


def find_swing_highs(candles: pd.DataFrame, window: int = 1) -> pd.DataFrame:
    """Return rows where high is greater than left and right highs."""
    swing_rows = []
    for index in range(window, len(candles) - window):
        current_high = candles.iloc[index]["high"]
        left_highs = candles.iloc[index - window : index]["high"]
        right_highs = candles.iloc[index + 1 : index + window + 1]["high"]
        if current_high > left_highs.max() and current_high > right_highs.max():
            swing_rows.append(candles.iloc[index])
    return pd.DataFrame(swing_rows)


def find_swing_lows(candles: pd.DataFrame, window: int = 1) -> pd.DataFrame:
    """Return rows where low is lower than left and right lows."""
    swing_rows = []
    for index in range(window, len(candles) - window):
        current_low = candles.iloc[index]["low"]
        left_lows = candles.iloc[index - window : index]["low"]
        right_lows = candles.iloc[index + 1 : index + window + 1]["low"]
        if current_low < left_lows.min() and current_low < right_lows.min():
            swing_rows.append(candles.iloc[index])
    return pd.DataFrame(swing_rows)


def tag_swings(candles: pd.DataFrame, window: int = 1) -> pd.DataFrame:
    """Add swing high and swing low flags per symbol."""
    tagged = candles.copy()
    tagged["is_swing_high"] = False
    tagged["is_swing_low"] = False

    for _, symbol_candles in tagged.groupby("symbol", sort=False):
        swing_high_indexes = find_swing_highs(symbol_candles, window).index
        swing_low_indexes = find_swing_lows(symbol_candles, window).index
        tagged.loc[swing_high_indexes, "is_swing_high"] = True
        tagged.loc[swing_low_indexes, "is_swing_low"] = True

    return tagged
