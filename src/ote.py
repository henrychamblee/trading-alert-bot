"""Entry refinement helpers: OTE, sweeps, displacement, and FVG."""

import pandas as pd


def calculate_ote_zone(swing_low: float, swing_high: float) -> dict:
    """Calculate a common 62% to 79% retracement zone."""
    price_range = swing_high - swing_low
    return {
        "lower": swing_high - (price_range * 0.79),
        "upper": swing_high - (price_range * 0.62),
    }


def price_in_ote_zone(price: float, zone: dict) -> bool:
    """Return True when price is inside the OTE zone."""
    return zone["lower"] <= price <= zone["upper"]


def calculate_entry_ote_zone(
    leg_low: float,
    leg_high: float,
    setup_direction: str,
    levels: list[float] | None = None,
) -> dict:
    """Calculate the OTE zone for bullish or bearish entry refinement."""
    levels = levels or [0.62, 0.66, 0.705, 0.786]
    price_range = leg_high - leg_low
    if price_range <= 0:
        return {"ote_zone_low": None, "ote_zone_high": None}

    if setup_direction == "bullish":
        prices = [leg_high - (price_range * level) for level in levels]
    elif setup_direction == "bearish":
        prices = [leg_low + (price_range * level) for level in levels]
    else:
        return {"ote_zone_low": None, "ote_zone_high": None}

    return {"ote_zone_low": min(prices), "ote_zone_high": max(prices)}


def is_ote_touched(candle: pd.Series, ote_zone: dict) -> bool:
    """Return True when a candle trades inside the OTE zone."""
    zone_low = ote_zone.get("ote_zone_low")
    zone_high = ote_zone.get("ote_zone_high")
    if zone_low is None or zone_high is None:
        return False
    return bool(candle["low"] <= zone_high and candle["high"] >= zone_low)


def detect_ote_touch(
    candles: pd.DataFrame,
    manipulation_leg: dict,
    setup_direction: str | None,
    levels: list[float] | None = None,
) -> dict:
    """Detect whether latest price has retraced into the OTE zone."""
    if candles.empty or not manipulation_leg.get("detected") or setup_direction is None:
        return {"ote_zone_low": None, "ote_zone_high": None, "ote_touched": False}

    start_time = manipulation_leg.get("manipulation_start")
    end_time = manipulation_leg.get("manipulation_end")
    leg_rows = candles[candles["timestamp"].isin([start_time, end_time])]
    if len(leg_rows) < 2:
        return {"ote_zone_low": None, "ote_zone_high": None, "ote_touched": False}

    leg_low = leg_rows["low"].min()
    leg_high = leg_rows["high"].max()
    zone = calculate_entry_ote_zone(leg_low, leg_high, setup_direction, levels)
    return {**zone, "ote_touched": is_ote_touched(candles.iloc[-1], zone)}


def _prior_level(candles: pd.DataFrame, setup_direction: str) -> float | None:
    """Find prior swing/session liquidity level before the latest candle."""
    if len(candles) < 2:
        return None

    prior = candles.iloc[:-1]
    latest_session = candles.iloc[-1].get("session") if "session" in candles.columns else None
    session_prior = prior[prior["session"] == latest_session] if latest_session else prior
    if session_prior.empty:
        session_prior = prior

    if setup_direction == "bullish":
        swing_lows = prior[prior["is_swing_low"]] if "is_swing_low" in prior.columns else prior.iloc[0:0]
        swing_level = swing_lows["low"].min() if not swing_lows.empty else None
        session_level = session_prior["low"].min()
        return min([level for level in [swing_level, session_level] if level is not None])

    if setup_direction == "bearish":
        swing_highs = prior[prior["is_swing_high"]] if "is_swing_high" in prior.columns else prior.iloc[0:0]
        swing_level = swing_highs["high"].max() if not swing_highs.empty else None
        session_level = session_prior["high"].max()
        return max([level for level in [swing_level, session_level] if level is not None])

    return None


def detect_liquidity_sweep(candles: pd.DataFrame, setup_direction: str | None) -> dict:
    """Detect a sweep and reclaim/rejection against prior swing or session liquidity."""
    if candles.empty or setup_direction is None:
        return {"sweep_confirmed": False, "sweep_level": None, "sweep_type": None}

    latest = candles.iloc[-1]
    level = _prior_level(candles, setup_direction)
    if level is None:
        return {"sweep_confirmed": False, "sweep_level": None, "sweep_type": None}

    if setup_direction == "bullish":
        confirmed = latest["low"] < level and latest["close"] > level
        return {
            "sweep_confirmed": bool(confirmed),
            "sweep_level": level,
            "sweep_type": "bullish" if confirmed else None,
        }

    confirmed = latest["high"] > level and latest["close"] < level
    return {
        "sweep_confirmed": bool(confirmed),
        "sweep_level": level,
        "sweep_type": "bearish" if confirmed else None,
    }


def _body(candle: pd.Series) -> float:
    return abs(candle["close"] - candle["open"])


def detect_displacement_candle(
    candles: pd.DataFrame,
    setup_direction: str | None,
    lookback: int = 3,
    body_multiplier: float = 1.25,
) -> dict:
    """Detect a strong candle closing in the setup direction."""
    if len(candles) < 2 or setup_direction is None:
        return {"displacement_confirmed": False, "displacement_timestamp": None}

    recent = candles.tail(max(lookback + 1, 2))
    latest = recent.iloc[-1]
    prior_bodies = recent.iloc[:-1].apply(_body, axis=1)
    average_body = prior_bodies.mean()
    latest_body = _body(latest)
    closes_in_direction = (
        latest["close"] > latest["open"]
        if setup_direction == "bullish"
        else latest["close"] < latest["open"]
    )
    confirmed = average_body > 0 and latest_body > average_body * body_multiplier and closes_in_direction
    return {
        "displacement_confirmed": bool(confirmed),
        "displacement_timestamp": latest["timestamp"] if confirmed else None,
    }


def detect_fvg(candles: pd.DataFrame) -> dict:
    """Detect a simple 3-candle fair value gap."""
    if len(candles) < 3:
        return {"fvg_detected": False, "fvg_type": None, "fvg_low": None, "fvg_high": None}

    recent = candles.tail(3)
    first = recent.iloc[0]
    third = recent.iloc[2]
    if first["high"] < third["low"]:
        return {
            "fvg_detected": True,
            "fvg_type": "bullish",
            "fvg_low": first["high"],
            "fvg_high": third["low"],
        }
    if first["low"] > third["high"]:
        return {
            "fvg_detected": True,
            "fvg_type": "bearish",
            "fvg_low": third["high"],
            "fvg_high": first["low"],
        }
    return {"fvg_detected": False, "fvg_type": None, "fvg_low": None, "fvg_high": None}


def build_entry_refinement(
    candles: pd.DataFrame,
    manipulation_leg: dict,
    setup_direction: str | None,
    settings: dict | None = None,
) -> dict:
    """Build all entry-refinement confirmations for a setup snapshot."""
    settings = settings or {}
    entry_settings = settings.get("entry", {})
    ote = detect_ote_touch(
        candles,
        manipulation_leg,
        setup_direction,
        entry_settings.get("ote_levels"),
    )
    sweep = detect_liquidity_sweep(candles, setup_direction)
    displacement = detect_displacement_candle(
        candles,
        setup_direction,
        entry_settings.get("displacement_lookback", 3),
        entry_settings.get("displacement_body_multiplier", 1.25),
    )
    fvg = detect_fvg(candles)
    return {**ote, **sweep, **displacement, **fvg}
