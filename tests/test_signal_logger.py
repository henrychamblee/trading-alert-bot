import csv

import pandas as pd

from src.logger import (
    append_signal_row,
    build_signal_row,
    review_signal_log,
)


def sample_signal_row(timestamp="2026-06-22 08:30:00", alert_state="SETUP_FORMING"):
    latest_candle = pd.Series(
        {
            "timestamp": pd.Timestamp(timestamp),
            "session": "New York",
        }
    )
    smt_result = {
        "smt_type": "bullish",
        "smt_mode": "live",
        "smt_timestamp": pd.Timestamp(timestamp),
        "smt_level": 20000,
    }
    manipulation_leg = {
        "manipulation_start": pd.Timestamp("2026-06-22 08:00:00"),
        "manipulation_end": pd.Timestamp("2026-06-22 08:20:00"),
        "manipulation_direction": "bullish",
    }
    setup_snapshot = {
        "alert_state": alert_state,
        "setup_score": 70,
        "suggested_entry_direction": "bullish",
        "nearest_deviation": {
            "deviation_level": 2.0,
            "deviation_price": 20100,
            "deviation_direction": "up",
        },
        "stop_loss": 19990,
        "take_profit": {
            "primary": 20050,
            "secondary": [{"name": "PDH", "price": 20200}],
        },
    }
    return build_signal_row(
        latest_candle,
        "NQ",
        smt_result,
        manipulation_leg,
        setup_snapshot,
        notes="Test row",
    )


def read_rows(path):
    with path.open("r", newline="", encoding="utf-8") as signal_file:
        return list(csv.DictReader(signal_file))


def test_append_signal_row_creates_signals_csv(tmp_path):
    log_path = tmp_path / "logs" / "signals.csv"

    saved = append_signal_row(log_path, sample_signal_row())

    assert saved is True
    assert log_path.exists()
    assert len(read_rows(log_path)) == 1


def test_append_signal_row_appends_new_signal_rows(tmp_path):
    log_path = tmp_path / "logs" / "signals.csv"

    append_signal_row(log_path, sample_signal_row())
    append_signal_row(log_path, sample_signal_row(timestamp="2026-06-22 08:35:00"))

    rows = read_rows(log_path)

    assert len(rows) == 2
    assert rows[1]["timestamp"] == "2026-06-22 08:35:00"


def test_append_signal_row_avoids_duplicate_rows(tmp_path):
    log_path = tmp_path / "logs" / "signals.csv"
    row = sample_signal_row()

    first_saved = append_signal_row(log_path, row)
    second_saved = append_signal_row(log_path, row)

    assert first_saved is True
    assert second_saved is False
    assert len(read_rows(log_path)) == 1


def test_review_signal_log_summarizes_saved_alerts(tmp_path):
    log_path = tmp_path / "logs" / "signals.csv"
    append_signal_row(log_path, sample_signal_row(alert_state="SETUP_FORMING"))
    append_signal_row(
        log_path,
        sample_signal_row(timestamp="2026-06-22 08:35:00", alert_state="A_PLUS_SETUP"),
    )

    summary = review_signal_log(log_path)

    assert summary["exists"] is True
    assert summary["total_alerts"] == 2
    assert summary["alert_counts"]["SETUP_FORMING"] == 1
    assert summary["alert_counts"]["A_PLUS_SETUP"] == 1
    assert summary["average_setup_score"] == 70
    assert len(summary["latest_alerts"]) == 2


def test_review_signal_log_handles_missing_file(tmp_path):
    summary = review_signal_log(tmp_path / "logs" / "signals.csv")

    assert summary == {"exists": False}
