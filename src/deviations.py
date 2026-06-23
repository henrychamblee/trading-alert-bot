"""Deviation and manipulation-leg helpers."""

import pandas as pd


def calculate_deviation_levels(anchor_price: float, leg_size: float) -> dict:
    """Return basic deviation levels from a manipulation leg."""
    return {
        "-2sd": anchor_price - (2 * leg_size),
        "-1sd": anchor_price - leg_size,
        "anchor": anchor_price,
        "+1sd": anchor_price + leg_size,
        "+2sd": anchor_price + (2 * leg_size),
    }


def calculate_manipulation_deviation_levels(
    candles: pd.DataFrame,
    manipulation_leg: dict,
    symbol: str = "NQ",
    levels: list[float] | None = None,
) -> list[dict]:
    """Project configurable standard deviation levels from a manipulation leg."""
    levels = levels or [2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
    if not manipulation_leg.get("detected"):
        return []

    symbol_candles = candles[candles["symbol"] == symbol] if "symbol" in candles.columns else candles
    start_time = manipulation_leg.get("manipulation_start")
    end_time = manipulation_leg.get("manipulation_end")
    leg_rows = symbol_candles[
        symbol_candles["timestamp"].isin([start_time, end_time])
    ].sort_values("timestamp")
    if len(leg_rows) < 2:
        return []

    start = leg_rows.iloc[0]
    end = leg_rows.iloc[-1]
    direction = manipulation_leg.get("manipulation_direction")

    if direction == "bullish":
        leg_low = min(start["low"], end["low"])
        leg_high = max(start["high"], end["high"])
        leg_range = leg_high - leg_low
        anchor = leg_high
        deviation_direction = "up"
        price_for_level = lambda level: anchor + (leg_range * level)
    elif direction == "bearish":
        leg_high = max(start["high"], end["high"])
        leg_low = min(start["low"], end["low"])
        leg_range = leg_high - leg_low
        anchor = leg_low
        deviation_direction = "down"
        price_for_level = lambda level: anchor - (leg_range * level)
    else:
        return []

    if leg_range <= 0:
        return []

    return [
        {
            "deviation_level": level,
            "deviation_price": price_for_level(level),
            "deviation_direction": deviation_direction,
        }
        for level in levels
    ]


def find_nearest_deviation(
    price: float,
    deviation_levels: list[dict],
    tolerance: float,
) -> dict:
    """Find the closest deviation and mark whether price is inside tolerance."""
    if not deviation_levels:
        return {
            "detected": False,
            "deviation_level": None,
            "deviation_price": None,
            "deviation_direction": None,
            "distance": None,
            "within_tolerance": False,
        }

    nearest = min(
        deviation_levels,
        key=lambda level: abs(price - level["deviation_price"]),
    )
    distance = abs(price - nearest["deviation_price"])
    return {
        **nearest,
        "detected": distance <= tolerance,
        "distance": distance,
        "within_tolerance": distance <= tolerance,
    }


def infer_distribution_direction(candles: pd.DataFrame, lookback: int = 3) -> str | None:
    """Infer whether price is currently distributing up or down."""
    if len(candles) < 2:
        return None

    recent = candles.tail(max(lookback, 2))
    first_close = recent.iloc[0]["close"]
    latest_close = recent.iloc[-1]["close"]
    if latest_close < first_close:
        return "down"
    if latest_close > first_close:
        return "up"
    return None


def _recent_symbol_candles(candles: pd.DataFrame, symbol: str, lookback: int) -> pd.DataFrame:
    """Return recent candles for the symbol used to anchor the manipulation leg."""
    symbol_candles = candles[candles["symbol"] == symbol] if "symbol" in candles.columns else candles
    return symbol_candles.sort_values("timestamp").tail(lookback)


def _last_prior_swing_pair(candles: pd.DataFrame, direction: str) -> tuple[pd.Series | None, pd.Series | None]:
    """Find the prior swing pair that defines the manipulation leg."""
    if "is_swing_high" not in candles.columns or "is_swing_low" not in candles.columns:
        return None, None

    if direction == "bullish":
        lows = candles[candles["is_swing_low"]]
        highs = candles[candles["is_swing_high"]]
        if lows.empty or highs.empty:
            return None, None
        end = highs.iloc[-1]
        prior_lows = lows[lows["timestamp"] < end["timestamp"]]
        if prior_lows.empty:
            return None, None
        return prior_lows.iloc[-1], end

    highs = candles[candles["is_swing_high"]]
    lows = candles[candles["is_swing_low"]]
    if highs.empty or lows.empty:
        return None, None
    end = lows.iloc[-1]
    prior_highs = highs[highs["timestamp"] < end["timestamp"]]
    if prior_highs.empty:
        return None, None
    return prior_highs.iloc[-1], end


def detect_manipulation_leg(
    candles: pd.DataFrame,
    smt_result: dict | None = None,
    symbol: str = "NQ",
    lookback: int = 20,
) -> dict:
    """Identify the prior manipulation leg using distribution-first context."""
    recent = _recent_symbol_candles(candles, symbol, lookback)
    if recent.empty:
        return {
            "detected": False,
            "manipulation_start": None,
            "manipulation_end": None,
            "manipulation_direction": None,
            "reason": "Missing symbol candles",
        }

    distribution_direction = infer_distribution_direction(recent)
    if distribution_direction is None:
        return {
            "detected": False,
            "manipulation_start": None,
            "manipulation_end": None,
            "manipulation_direction": None,
            "reason": "No clear distribution direction",
        }

    manipulation_direction = "bullish" if distribution_direction == "down" else "bearish"
    start, end = _last_prior_swing_pair(recent, manipulation_direction)
    if start is None or end is None:
        return {
            "detected": False,
            "manipulation_start": None,
            "manipulation_end": None,
            "manipulation_direction": manipulation_direction,
            "reason": "Not enough recent swing structure",
        }

    smt_confluence = bool((smt_result or {}).get("detected"))
    return {
        "detected": True,
        "manipulation_start": start["timestamp"],
        "manipulation_end": end["timestamp"],
        "manipulation_direction": manipulation_direction,
        "distribution_direction": distribution_direction,
        "smt_confluence": smt_confluence,
        "session": end.get("session"),
        "reason": "Distribution-first manipulation leg identified.",
    }
