import pandas as pd
import pytest

from src.ote import (
    build_entry_refinement,
    calculate_entry_ote_zone,
    detect_displacement_candle,
    detect_fvg,
    detect_liquidity_sweep,
    detect_ote_touch,
    is_ote_touched,
)


def test_calculate_entry_ote_zone_for_bullish_setup():
    zone = calculate_entry_ote_zone(100, 200, "bullish", [0.62, 0.786])

    assert zone["ote_zone_low"] == pytest.approx(121.4)
    assert zone["ote_zone_high"] == pytest.approx(138.0)


def test_calculate_entry_ote_zone_for_bearish_setup():
    zone = calculate_entry_ote_zone(100, 200, "bearish", [0.62, 0.786])

    assert zone["ote_zone_low"] == pytest.approx(162.0)
    assert zone["ote_zone_high"] == pytest.approx(178.6)


def test_is_ote_touched_detects_candle_overlap():
    candle = pd.Series({"high": 140, "low": 130})
    zone = {"ote_zone_low": 121.4, "ote_zone_high": 138.0}

    assert is_ote_touched(candle, zone) is True


def test_detect_ote_touch_from_manipulation_leg():
    candles = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-06-22 08:30:00",
                    "2026-06-22 08:40:00",
                    "2026-06-22 08:50:00",
                ]
            ),
            "high": [101, 200, 139],
            "low": [100, 190, 130],
        }
    )
    leg = {
        "detected": True,
        "manipulation_start": pd.Timestamp("2026-06-22 08:30:00"),
        "manipulation_end": pd.Timestamp("2026-06-22 08:40:00"),
    }

    result = detect_ote_touch(candles, leg, "bullish", [0.62, 0.786])

    assert result["ote_touched"] is True


def test_detect_bullish_liquidity_sweep():
    candles = pd.DataFrame(
        {
            "session": ["New York", "New York", "New York"],
            "high": [110, 108, 107],
            "low": [100, 102, 99],
            "close": [105, 106, 103],
            "is_swing_low": [True, False, False],
            "is_swing_high": [False, False, False],
        }
    )

    result = detect_liquidity_sweep(candles, "bullish")

    assert result["sweep_confirmed"] is True
    assert result["sweep_level"] == 100
    assert result["sweep_type"] == "bullish"


def test_detect_bearish_liquidity_sweep():
    candles = pd.DataFrame(
        {
            "session": ["New York", "New York", "New York"],
            "high": [110, 108, 111],
            "low": [100, 102, 103],
            "close": [105, 106, 109],
            "is_swing_low": [False, False, False],
            "is_swing_high": [True, False, False],
        }
    )

    result = detect_liquidity_sweep(candles, "bearish")

    assert result["sweep_confirmed"] is True
    assert result["sweep_level"] == 110
    assert result["sweep_type"] == "bearish"


def test_detect_displacement_candle_requires_large_directional_body():
    candles = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-06-22 08:30:00",
                    "2026-06-22 08:35:00",
                    "2026-06-22 08:40:00",
                ]
            ),
            "open": [100, 101, 100],
            "high": [103, 104, 112],
            "low": [99, 100, 99],
            "close": [101, 102, 110],
        }
    )

    result = detect_displacement_candle(candles, "bullish", lookback=2, body_multiplier=1.25)

    assert result["displacement_confirmed"] is True
    assert result["displacement_timestamp"] == pd.Timestamp("2026-06-22 08:40:00")


def test_detect_bullish_fvg():
    candles = pd.DataFrame(
        {
            "high": [100, 105, 115],
            "low": [95, 101, 110],
        }
    )

    result = detect_fvg(candles)

    assert result["fvg_detected"] is True
    assert result["fvg_type"] == "bullish"
    assert result["fvg_low"] == 100
    assert result["fvg_high"] == 110


def test_detect_bearish_fvg():
    candles = pd.DataFrame(
        {
            "high": [110, 105, 95],
            "low": [100, 96, 90],
        }
    )

    result = detect_fvg(candles)

    assert result["fvg_detected"] is True
    assert result["fvg_type"] == "bearish"
    assert result["fvg_low"] == 95
    assert result["fvg_high"] == 100


def test_build_entry_refinement_returns_all_phase_7_fields():
    candles = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-06-22 08:30:00",
                    "2026-06-22 08:35:00",
                    "2026-06-22 08:40:00",
                ]
            ),
            "session": ["New York", "New York", "New York"],
            "open": [100, 101, 100],
            "high": [101, 200, 139],
            "low": [100, 190, 99],
            "close": [101, 195, 130],
            "is_swing_low": [True, False, False],
            "is_swing_high": [False, True, False],
        }
    )
    leg = {
        "detected": True,
        "manipulation_start": pd.Timestamp("2026-06-22 08:30:00"),
        "manipulation_end": pd.Timestamp("2026-06-22 08:35:00"),
    }

    result = build_entry_refinement(candles, leg, "bullish")

    assert "ote_touched" in result
    assert "sweep_confirmed" in result
    assert "displacement_confirmed" in result
    assert "fvg_detected" in result
