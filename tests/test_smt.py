import pandas as pd

from src.smt import detect_smt_divergence


def test_detect_smt_divergence_when_only_nq_makes_higher_high():
    nq = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-22 08:30:00", "2026-06-22 08:35:00"]),
            "high": [100, 110],
            "low": [95, 98],
        }
    )
    es = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-22 08:30:00", "2026-06-22 08:35:00"]),
            "high": [100, 99],
            "low": [95, 96],
        }
    )

    result = detect_smt_divergence(nq, es)

    assert result["detected"] is True
    assert result["direction"] == "bearish"
    assert result["smt_type"] == "bearish"
    assert result["smt_mode"] == "live"
    assert result["smt_level"] == 110


def test_detect_smt_divergence_returns_false_without_data():
    result = detect_smt_divergence(pd.DataFrame(), pd.DataFrame())

    assert result["detected"] is False


def test_detect_smt_divergence_when_only_es_makes_lower_low():
    nq = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-22 08:30:00", "2026-06-22 08:35:00"]),
            "high": [100, 99],
            "low": [95, 96],
        }
    )
    es = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-22 08:30:00", "2026-06-22 08:35:00"]),
            "high": [100, 99],
            "low": [95, 90],
        }
    )

    result = detect_smt_divergence(nq, es)

    assert result["detected"] is True
    assert result["smt_type"] == "bullish"
    assert result["smt_mode"] == "live"
    assert result["smt_level"] == 90


def test_detect_gap_smt_when_only_nq_opens_above_prior_swing_high():
    nq = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-06-22 08:30:00",
                    "2026-06-22 08:35:00",
                    "2026-06-22 08:40:00",
                ]
            ),
            "open": [99, 101, 112],
            "high": [100, 110, 113],
            "low": [95, 98, 109],
            "is_swing_high": [False, True, False],
            "is_swing_low": [True, False, False],
        }
    )
    es = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-06-22 08:30:00",
                    "2026-06-22 08:35:00",
                    "2026-06-22 08:40:00",
                ]
            ),
            "open": [99, 101, 104],
            "high": [100, 108, 105],
            "low": [95, 98, 99],
            "is_swing_high": [False, True, False],
            "is_swing_low": [True, False, False],
        }
    )

    result = detect_smt_divergence(nq, es)

    assert result["detected"] is True
    assert result["smt_type"] == "bearish"
    assert result["smt_mode"] == "gap"
    assert result["smt_level"] == 112
