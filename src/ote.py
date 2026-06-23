"""Optimal Trade Entry retracement helpers."""


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

