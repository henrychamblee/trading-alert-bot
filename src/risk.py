"""Risk placeholders for stop loss, take profit, and invalidation levels."""


def build_risk_plan(entry: float, stop: float, target: float) -> dict:
    """Create a simple risk plan for an alert."""
    risk = abs(entry - stop)
    reward = abs(target - entry)
    reward_to_risk = reward / risk if risk else None
    return {
        "entry": entry,
        "stop_loss": stop,
        "take_profit": target,
        "reward_to_risk": reward_to_risk,
    }


def calculate_stop_loss(
    setup_direction: str,
    smt_result: dict,
    current_price: float,
    max_stop_points: float,
) -> float:
    """Suggest a stop from SMT level, falling back to max stop distance."""
    smt_level = smt_result.get("smt_level")
    if setup_direction == "bullish":
        if smt_level is not None:
            return smt_level
        return current_price - max_stop_points

    if setup_direction == "bearish":
        if smt_level is not None:
            return smt_level
        return current_price + max_stop_points

    return current_price


def latest_session_extreme(candles, setup_direction: str) -> float | None:
    """Return the latest session high or low target."""
    if candles.empty or "session" not in candles.columns:
        return None

    latest_session = candles.iloc[-1]["session"]
    session_candles = candles[candles["session"] == latest_session]
    if session_candles.empty:
        return None

    if setup_direction == "bullish":
        return session_candles["high"].max()
    if setup_direction == "bearish":
        return session_candles["low"].min()
    return None


def calculate_take_profit(setup_direction: str, candles) -> dict:
    """Suggest primary and secondary liquidity targets."""
    if candles.empty:
        return {"primary": None, "secondary": []}

    latest = candles.iloc[-1]
    secondary = []
    for key in ("pdh", "pdl"):
        value = latest.get(key)
        if value == value:
            secondary.append({"name": key.upper(), "price": value})

    session_extreme = latest_session_extreme(candles, setup_direction)
    if session_extreme is not None:
        secondary.append(
            {
                "name": "SESSION_HIGH" if setup_direction == "bullish" else "SESSION_LOW",
                "price": session_extreme,
            }
        )

    primary = latest.get("midnight_open")
    if primary != primary:
        primary = None

    return {"primary": primary, "secondary": secondary}


def has_target_liquidity(take_profit: dict) -> bool:
    """Return True when at least one target is available."""
    return take_profit.get("primary") is not None or bool(take_profit.get("secondary"))
