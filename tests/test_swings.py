import pandas as pd

from src.swings import find_swing_highs, find_swing_lows, tag_swings


def test_find_swing_highs_detects_local_high():
    candles = pd.DataFrame(
        {
            "high": [10, 12, 15, 11, 9],
            "low": [5, 6, 7, 6, 4],
        }
    )

    swings = find_swing_highs(candles)

    assert len(swings) == 1
    assert swings.iloc[0]["high"] == 15


def test_find_swing_lows_detects_local_low():
    candles = pd.DataFrame(
        {
            "high": [10, 12, 15, 11, 9],
            "low": [5, 6, 3, 6, 4],
        }
    )

    swings = find_swing_lows(candles)

    assert len(swings) == 1
    assert swings.iloc[0]["low"] == 3


def test_find_swings_supports_configurable_lookback():
    candles = pd.DataFrame(
        {
            "high": [10, 12, 16, 14, 11],
            "low": [6, 5, 4, 5, 6],
        }
    )

    highs = find_swing_highs(candles, window=2)
    lows = find_swing_lows(candles, window=2)

    assert len(highs) == 1
    assert highs.iloc[0]["high"] == 16
    assert len(lows) == 1
    assert lows.iloc[0]["low"] == 4


def test_tag_swings_flags_each_symbol_independently():
    candles = pd.DataFrame(
        {
            "symbol": ["NQ", "NQ", "NQ", "ES", "ES", "ES"],
            "high": [10, 15, 11, 20, 25, 21],
            "low": [7, 8, 6, 17, 18, 16],
        }
    )

    tagged = tag_swings(candles, window=1)

    assert bool(tagged.loc[1, "is_swing_high"]) is True
    assert bool(tagged.loc[4, "is_swing_high"]) is True
