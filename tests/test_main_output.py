import pandas as pd

from src.main import print_market_structure_summary


def test_phase_4_summary_prints_no_setup_message(capsys):
    candles = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-22 08:30:00"]),
            "session": ["New York"],
            "midnight_open": [100],
            "pdh": [120],
            "pdl": [90],
            "is_swing_high": [False],
            "is_swing_low": [False],
        }
    )

    print_market_structure_summary(
        candles,
        {"smt_type": None, "smt_mode": None, "smt_timestamp": None, "smt_level": None},
        {
            "manipulation_start": None,
            "manipulation_end": None,
            "manipulation_direction": None,
        },
        {
            "alert_state": "NO_SETUP",
            "setup_score": 0,
            "suggested_entry_direction": None,
            "stop_loss": None,
            "take_profit": {"primary": None, "secondary": []},
            "nearest_deviation": {
                "deviation_level": None,
                "deviation_price": None,
                "deviation_direction": None,
            },
        },
    )

    output = capsys.readouterr().out

    assert "Phase 4 Summary" in output
    assert "Current session: New York" in output
    assert "PDH/PDL: 120 / 90" in output
    assert "Latest SMT: none" in output
    assert "Manipulation leg: None -> None" in output
    assert "Nearest deviation: level=None, price=None, direction=None" in output
    assert "Setup score: 0" in output
    assert "Alert state: NO_SETUP" in output
    assert "Suggested direction: None" in output
    assert "Stop loss: None" in output
    assert "Take profit: {'primary': None, 'secondary': []}" in output
    assert "No setup found from sample data." in output
