"""Momentum checks for detecting slowdown at key deviation levels."""

import pandas as pd


def has_loss_of_momentum(candles: pd.DataFrame) -> bool:
    """Return True when the latest candle body is smaller than the prior body."""
    if len(candles) < 2:
        return False

    previous = candles.iloc[-2]
    latest = candles.iloc[-1]
    previous_body = abs(previous["close"] - previous["open"])
    latest_body = abs(latest["close"] - latest["open"])
    return latest_body < previous_body


def candle_body(candle: pd.Series) -> float:
    """Return absolute candle body size."""
    return abs(candle["close"] - candle["open"])


def has_body_shrink(candles: pd.DataFrame, lookback: int = 3, shrink_ratio: float = 0.75) -> bool:
    """Return True when the latest body is smaller than prior average body."""
    if len(candles) < 2:
        return False

    recent = candles.tail(max(lookback, 2))
    prior_bodies = recent.iloc[:-1].apply(candle_body, axis=1)
    latest_body = candle_body(recent.iloc[-1])
    prior_average = prior_bodies.mean()
    return bool(prior_average > 0 and latest_body <= prior_average * shrink_ratio)


def has_rejection_wick(
    latest_candle: pd.Series,
    setup_direction: str,
    wick_ratio: float = 1.5,
) -> bool:
    """Detect a rejection wick in the opposite direction of the setup."""
    body = max(candle_body(latest_candle), 0.01)
    upper_wick = latest_candle["high"] - max(latest_candle["open"], latest_candle["close"])
    lower_wick = min(latest_candle["open"], latest_candle["close"]) - latest_candle["low"]

    if setup_direction == "bullish":
        return bool(lower_wick >= body * wick_ratio)
    if setup_direction == "bearish":
        return bool(upper_wick >= body * wick_ratio)
    return False


def has_failed_continuation(
    candles: pd.DataFrame,
    setup_direction: str,
    bars: int = 2,
) -> bool:
    """Detect failure to continue after touching a deviation area."""
    if len(candles) < bars + 1:
        return False

    recent = candles.tail(bars + 1)
    touch = recent.iloc[0]
    latest = recent.iloc[-1]

    if setup_direction == "bullish":
        return bool(latest["low"] >= touch["low"] and latest["close"] > touch["close"])
    if setup_direction == "bearish":
        return bool(latest["high"] <= touch["high"] and latest["close"] < touch["close"])
    return False


def detect_loss_of_momentum(
    candles: pd.DataFrame,
    setup_direction: str,
    settings: dict | None = None,
) -> dict:
    """Combine body shrink, rejection wick, and failed continuation checks."""
    if candles.empty:
        return {
            "detected": False,
            "body_shrinking": False,
            "rejection_wick": False,
            "failed_continuation": False,
        }

    settings = settings or {}
    body_shrinking = has_body_shrink(
        candles,
        settings.get("body_shrink_lookback", 3),
        settings.get("body_shrink_ratio", 0.75),
    )
    rejection_wick = has_rejection_wick(
        candles.iloc[-1],
        setup_direction,
        settings.get("rejection_wick_ratio", 1.5),
    )
    failed_continuation = has_failed_continuation(
        candles,
        setup_direction,
        settings.get("failed_continuation_bars", 2),
    )

    return {
        "detected": bool(body_shrinking or rejection_wick or failed_continuation),
        "body_shrinking": body_shrinking,
        "rejection_wick": rejection_wick,
        "failed_continuation": failed_continuation,
    }
