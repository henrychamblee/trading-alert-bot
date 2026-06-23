"""SMT divergence detection between NQ and ES."""

import pandas as pd


def _empty_result(reason: str) -> dict:
    """Return a consistent empty SMT result."""
    return {
        "detected": False,
        "direction": None,
        "smt_type": None,
        "smt_mode": None,
        "smt_timestamp": None,
        "smt_level": None,
        "reason": reason,
    }


def _recent_swings(candles: pd.DataFrame, swing_column: str, lookback: int) -> pd.DataFrame:
    """Return recent swing rows, or all rows as a fallback for simple tests."""
    if swing_column in candles.columns:
        swings = candles[candles[swing_column]].tail(lookback)
        if len(swings) >= 2:
            return swings
    return candles.tail(max(lookback, 2))


def _made_higher_high(candles: pd.DataFrame, lookback: int) -> tuple[bool, pd.Series | None]:
    """Return whether recent swing structure made a higher high."""
    swings = _recent_swings(candles, "is_swing_high", lookback)
    if len(swings) < 2:
        return False, None
    previous = swings.iloc[-2]
    latest = swings.iloc[-1]
    return bool(latest["high"] > previous["high"]), latest


def _made_lower_low(candles: pd.DataFrame, lookback: int) -> tuple[bool, pd.Series | None]:
    """Return whether recent swing structure made a lower low."""
    swings = _recent_swings(candles, "is_swing_low", lookback)
    if len(swings) < 2:
        return False, None
    previous = swings.iloc[-2]
    latest = swings.iloc[-1]
    return bool(latest["low"] < previous["low"]), latest


def _detect_gap_smt(nq_candles: pd.DataFrame, es_candles: pd.DataFrame, lookback: int) -> dict:
    """Detect gap SMT when one symbol opens through a prior swing and the other does not."""
    if "open" not in nq_candles.columns or "open" not in es_candles.columns:
        return _empty_result("Open prices are required for gap SMT")

    nq_high_swings = _recent_swings(nq_candles.iloc[:-1], "is_swing_high", lookback)
    es_high_swings = _recent_swings(es_candles.iloc[:-1], "is_swing_high", lookback)
    nq_low_swings = _recent_swings(nq_candles.iloc[:-1], "is_swing_low", lookback)
    es_low_swings = _recent_swings(es_candles.iloc[:-1], "is_swing_low", lookback)

    if min(len(nq_high_swings), len(es_high_swings), len(nq_low_swings), len(es_low_swings)) < 1:
        return _empty_result("Not enough prior swing data for gap SMT")

    nq_latest = nq_candles.iloc[-1]
    es_latest = es_candles.iloc[-1]
    nq_gapped_above = nq_latest["open"] > nq_high_swings.iloc[-1]["high"]
    es_gapped_above = es_latest["open"] > es_high_swings.iloc[-1]["high"]
    nq_gapped_below = nq_latest["open"] < nq_low_swings.iloc[-1]["low"]
    es_gapped_below = es_latest["open"] < es_low_swings.iloc[-1]["low"]

    if nq_gapped_above != es_gapped_above:
        leader = nq_latest if nq_gapped_above else es_latest
        return {
            "detected": True,
            "direction": "bearish",
            "smt_type": "bearish",
            "smt_mode": "gap",
            "smt_timestamp": leader.get("timestamp"),
            "smt_level": leader["open"],
            "reason": "One index gapped above a prior swing high while the other did not.",
        }

    if nq_gapped_below != es_gapped_below:
        leader = nq_latest if nq_gapped_below else es_latest
        return {
            "detected": True,
            "direction": "bullish",
            "smt_type": "bullish",
            "smt_mode": "gap",
            "smt_timestamp": leader.get("timestamp"),
            "smt_level": leader["open"],
            "reason": "One index gapped below a prior swing low while the other did not.",
        }

    return _empty_result("No gap SMT found")


def detect_smt_divergence(
    nq_candles: pd.DataFrame,
    es_candles: pd.DataFrame,
    lookback: int = 3,
    include_gap: bool = True,
) -> dict:
    """Detect live or gap SMT from recent swing highs and lows."""
    if nq_candles.empty or es_candles.empty:
        return _empty_result("Missing candle data")

    if include_gap:
        gap_result = _detect_gap_smt(nq_candles, es_candles, lookback)
        if gap_result["detected"]:
            return gap_result

    nq_made_higher_high, nq_high = _made_higher_high(nq_candles, lookback)
    es_made_higher_high, es_high = _made_higher_high(es_candles, lookback)
    if nq_made_higher_high != es_made_higher_high:
        leader = nq_high if nq_made_higher_high else es_high
        return {
            "detected": True,
            "direction": "bearish",
            "smt_type": "bearish",
            "smt_mode": "live",
            "smt_timestamp": leader.get("timestamp"),
            "smt_level": leader["high"],
            "reason": "One index made a higher high while the other did not.",
        }

    nq_made_lower_low, nq_low = _made_lower_low(nq_candles, lookback)
    es_made_lower_low, es_low = _made_lower_low(es_candles, lookback)
    if nq_made_lower_low != es_made_lower_low:
        leader = nq_low if nq_made_lower_low else es_low
        return {
            "detected": True,
            "direction": "bullish",
            "smt_type": "bullish",
            "smt_mode": "live",
            "smt_timestamp": leader.get("timestamp"),
            "smt_level": leader["low"],
            "reason": "One index made a lower low while the other did not.",
        }

    return _empty_result("No SMT divergence found")
