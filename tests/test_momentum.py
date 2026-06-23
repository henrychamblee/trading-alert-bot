import pandas as pd

from src.momentum import (
    detect_loss_of_momentum,
    has_body_shrink,
    has_failed_continuation,
    has_rejection_wick,
)


def test_has_body_shrink_detects_smaller_latest_body():
    candles = pd.DataFrame(
        {
            "open": [100, 100, 100],
            "high": [110, 110, 105],
            "low": [95, 95, 98],
            "close": [108, 106, 101],
        }
    )

    assert has_body_shrink(candles, lookback=3, shrink_ratio=0.75) is True


def test_has_rejection_wick_detects_bullish_lower_wick():
    candle = pd.Series({"open": 100, "high": 103, "low": 90, "close": 101})

    assert has_rejection_wick(candle, "bullish", wick_ratio=1.5) is True


def test_has_failed_continuation_detects_bearish_failure():
    candles = pd.DataFrame(
        {
            "open": [100, 101, 100],
            "high": [110, 108, 107],
            "low": [98, 97, 96],
            "close": [105, 100, 99],
        }
    )

    assert has_failed_continuation(candles, "bearish", bars=2) is True


def test_detect_loss_of_momentum_returns_details():
    candles = pd.DataFrame(
        {
            "open": [100, 100, 100],
            "high": [110, 110, 103],
            "low": [95, 95, 90],
            "close": [108, 106, 101],
        }
    )

    result = detect_loss_of_momentum(candles, "bullish")

    assert result["detected"] is True
    assert "body_shrinking" in result
