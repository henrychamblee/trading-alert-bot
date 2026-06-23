import pandas as pd

from src.risk import calculate_stop_loss, calculate_take_profit, has_target_liquidity


def test_calculate_stop_loss_uses_smt_level_when_available():
    bullish_stop = calculate_stop_loss("bullish", {"smt_level": 95}, 105, 15)
    bearish_stop = calculate_stop_loss("bearish", {"smt_level": 115}, 105, 15)

    assert bullish_stop == 95
    assert bearish_stop == 115


def test_calculate_stop_loss_uses_max_stop_fallback():
    bullish_stop = calculate_stop_loss("bullish", {"smt_level": None}, 105, 15)
    bearish_stop = calculate_stop_loss("bearish", {"smt_level": None}, 105, 15)

    assert bullish_stop == 90
    assert bearish_stop == 120


def test_calculate_take_profit_uses_midnight_open_and_liquidity_targets():
    candles = pd.DataFrame(
        {
            "session": ["New York", "New York"],
            "high": [110, 115],
            "low": [95, 98],
            "midnight_open": [100, 100],
            "pdh": [120, 120],
            "pdl": [90, 90],
        }
    )

    take_profit = calculate_take_profit("bullish", candles)

    assert take_profit["primary"] == 100
    assert has_target_liquidity(take_profit) is True
    assert {"name": "SESSION_HIGH", "price": 115} in take_profit["secondary"]
