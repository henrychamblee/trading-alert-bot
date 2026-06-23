import pandas as pd

from src.deviations import (
    calculate_manipulation_deviation_levels,
    detect_manipulation_leg,
    find_nearest_deviation,
)


def test_detect_manipulation_leg_finds_prior_bullish_leg_when_distributing_down():
    candles = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-06-22 08:30:00",
                    "2026-06-22 08:35:00",
                    "2026-06-22 08:40:00",
                    "2026-06-22 08:45:00",
                ]
            ),
            "symbol": ["NQ", "NQ", "NQ", "NQ"],
            "session": ["New York", "New York", "New York", "New York"],
            "high": [100, 108, 110, 106],
            "low": [95, 96, 102, 99],
            "close": [98, 106, 104, 100],
            "is_swing_low": [True, False, False, False],
            "is_swing_high": [False, False, True, False],
        }
    )
    smt = {"detected": True, "smt_type": "bearish"}

    result = detect_manipulation_leg(candles, smt, symbol="NQ", lookback=10)

    assert result["detected"] is True
    assert result["manipulation_direction"] == "bullish"
    assert result["manipulation_start"] == pd.Timestamp("2026-06-22 08:30:00")
    assert result["manipulation_end"] == pd.Timestamp("2026-06-22 08:40:00")
    assert result["smt_confluence"] is True


def test_detect_manipulation_leg_finds_prior_bearish_leg_when_distributing_up():
    candles = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-06-22 08:30:00",
                    "2026-06-22 08:35:00",
                    "2026-06-22 08:40:00",
                    "2026-06-22 08:45:00",
                ]
            ),
            "symbol": ["NQ", "NQ", "NQ", "NQ"],
            "session": ["New York", "New York", "New York", "New York"],
            "high": [110, 108, 104, 107],
            "low": [104, 100, 96, 101],
            "close": [106, 101, 103, 108],
            "is_swing_high": [True, False, False, False],
            "is_swing_low": [False, False, True, False],
        }
    )
    smt = {"detected": True, "smt_type": "bullish"}

    result = detect_manipulation_leg(candles, smt, symbol="NQ", lookback=10)

    assert result["detected"] is True
    assert result["manipulation_direction"] == "bearish"
    assert result["manipulation_start"] == pd.Timestamp("2026-06-22 08:30:00")
    assert result["manipulation_end"] == pd.Timestamp("2026-06-22 08:40:00")


def test_calculate_manipulation_deviation_levels_for_bullish_leg():
    candles = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-22 08:30:00", "2026-06-22 08:40:00"]),
            "symbol": ["NQ", "NQ"],
            "high": [101, 110],
            "low": [100, 105],
        }
    )
    leg = {
        "detected": True,
        "manipulation_start": pd.Timestamp("2026-06-22 08:30:00"),
        "manipulation_end": pd.Timestamp("2026-06-22 08:40:00"),
        "manipulation_direction": "bullish",
    }

    levels = calculate_manipulation_deviation_levels(candles, leg, levels=[2.0])

    assert levels[0]["deviation_level"] == 2.0
    assert levels[0]["deviation_price"] == 130
    assert levels[0]["deviation_direction"] == "up"


def test_calculate_manipulation_deviation_levels_for_bearish_leg():
    candles = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-22 08:30:00", "2026-06-22 08:40:00"]),
            "symbol": ["NQ", "NQ"],
            "high": [110, 105],
            "low": [104, 100],
        }
    )
    leg = {
        "detected": True,
        "manipulation_start": pd.Timestamp("2026-06-22 08:30:00"),
        "manipulation_end": pd.Timestamp("2026-06-22 08:40:00"),
        "manipulation_direction": "bearish",
    }

    levels = calculate_manipulation_deviation_levels(candles, leg, levels=[2.0])

    assert levels[0]["deviation_price"] == 80
    assert levels[0]["deviation_direction"] == "down"


def test_find_nearest_deviation_detects_price_within_tolerance():
    levels = [
        {"deviation_level": 2.0, "deviation_price": 130, "deviation_direction": "up"},
        {"deviation_level": 2.5, "deviation_price": 135, "deviation_direction": "up"},
    ]

    nearest = find_nearest_deviation(132, levels, tolerance=5)

    assert nearest["within_tolerance"] is True
    assert nearest["deviation_level"] == 2.0
