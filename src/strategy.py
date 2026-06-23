"""Strategy orchestration for alert-only trade setup detection."""

import pandas as pd

from alerts import format_alert
from deviations import calculate_manipulation_deviation_levels, find_nearest_deviation
from momentum import detect_loss_of_momentum, has_loss_of_momentum
from risk import calculate_stop_loss, calculate_take_profit, has_target_liquidity
from smt import detect_smt_divergence


def evaluate_market(candles: pd.DataFrame) -> list[str]:
    """Evaluate current candles and return alert messages.

    This is placeholder orchestration. Future versions should combine SMT,
    sessions, swings, deviations, OTE, risk, invalidations, and exits.
    """
    alerts = []
    nq_candles = candles[candles["symbol"] == "NQ"]
    es_candles = candles[candles["symbol"] == "ES"]

    smt_result = detect_smt_divergence(nq_candles, es_candles)
    if smt_result["detected"]:
        alerts.append(format_alert("SMT divergence forming", smt_result))

    if has_loss_of_momentum(nq_candles):
        alerts.append(
            format_alert(
                "NQ loss of momentum",
                {"symbol": "NQ", "note": "Placeholder momentum slowdown detected."},
            )
        )

    return alerts


def get_setup_direction(smt_result: dict) -> str | None:
    """Translate SMT type into suggested alert direction."""
    if smt_result.get("smt_type") == "bullish":
        return "bullish"
    if smt_result.get("smt_type") == "bearish":
        return "bearish"
    return None


def score_setup(
    manipulation_leg: dict,
    nearest_deviation: dict,
    smt_result: dict,
    momentum_result: dict,
    target_available: bool,
    scoring_settings: dict | None = None,
) -> dict:
    """Score an alert-only setup from 0 to 100."""
    scoring_settings = scoring_settings or {}
    score = 0
    breakdown = {}

    checks = {
        "manipulation_leg": bool(manipulation_leg.get("detected")),
        "price_at_deviation": bool(nearest_deviation.get("within_tolerance")),
        "smt_aligned": bool(smt_result.get("detected")),
        "loss_of_momentum": bool(momentum_result.get("detected")),
        "target_liquidity_available": bool(target_available),
    }

    defaults = {
        "manipulation_leg": 20,
        "price_at_deviation": 25,
        "smt_aligned": 25,
        "loss_of_momentum": 20,
        "target_liquidity_available": 10,
    }

    for key, passed in checks.items():
        points = scoring_settings.get(key, defaults[key])
        earned = points if passed else 0
        breakdown[key] = earned
        score += earned

    return {"score": min(score, 100), "breakdown": breakdown}


def determine_alert_state(
    score: int,
    setup_direction: str | None,
    nearest_deviation: dict,
    momentum_result: dict,
    invalidated: bool = False,
    a_plus_threshold: int = 85,
) -> str:
    """Determine the current alert state without placing trades."""
    if invalidated:
        return "INVALIDATED"
    if setup_direction is None:
        return "NO_SETUP"
    if not nearest_deviation.get("within_tolerance") and score < a_plus_threshold:
        return "SETUP_FORMING" if score > 0 else "NO_SETUP"
    if score >= a_plus_threshold and momentum_result.get("detected"):
        return "ENTRY_ALERT"
    if score >= a_plus_threshold:
        return "A_PLUS_SETUP"
    return "SETUP_FORMING"


def build_setup_snapshot(
    candles: pd.DataFrame,
    smt_result: dict,
    manipulation_leg: dict,
    settings: dict | None = None,
    symbol: str = "NQ",
) -> dict:
    """Build a full alert-only setup snapshot for display and messaging."""
    settings = settings or {}
    symbol_candles = candles[candles["symbol"] == symbol] if "symbol" in candles.columns else candles
    if symbol_candles.empty:
        return {"alert_state": "NO_SETUP", "setup_score": 0}

    latest = symbol_candles.sort_values("timestamp").iloc[-1]
    current_price = latest["close"]
    setup_direction = get_setup_direction(smt_result)
    deviation_levels = calculate_manipulation_deviation_levels(
        candles,
        manipulation_leg,
        symbol,
        settings.get("market_structure", {}).get("deviation_levels"),
    )
    tolerance = settings.get("deviations", {}).get("tolerance_points", {}).get(symbol, 5)
    nearest_deviation = find_nearest_deviation(current_price, deviation_levels, tolerance)
    momentum_result = detect_loss_of_momentum(
        symbol_candles,
        setup_direction or "",
        settings.get("momentum", {}),
    )
    take_profit = calculate_take_profit(setup_direction or "", symbol_candles)
    scoring = score_setup(
        manipulation_leg,
        nearest_deviation,
        smt_result,
        momentum_result,
        has_target_liquidity(take_profit),
        settings.get("scoring", {}),
    )
    max_stop = settings.get("risk", {}).get("max_stop_points", {}).get(symbol, 15)
    stop_loss = (
        calculate_stop_loss(setup_direction, smt_result, current_price, max_stop)
        if setup_direction
        else None
    )
    invalidated = bool(
        setup_direction == "bullish"
        and stop_loss is not None
        and current_price <= stop_loss
        or setup_direction == "bearish"
        and stop_loss is not None
        and current_price >= stop_loss
    )
    alert_state = determine_alert_state(
        scoring["score"],
        setup_direction,
        nearest_deviation,
        momentum_result,
        invalidated,
        settings.get("scoring", {}).get("a_plus_threshold", 85),
    )

    return {
        "alert_state": alert_state,
        "setup_score": scoring["score"],
        "score_breakdown": scoring["breakdown"],
        "suggested_entry_direction": setup_direction,
        "nearest_deviation": nearest_deviation,
        "loss_of_momentum": momentum_result,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "current_price": current_price,
    }
