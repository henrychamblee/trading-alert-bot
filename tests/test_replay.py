import csv

import pandas as pd

from src.replay import (
    iter_replay_steps,
    load_replay_data,
    run_replay,
    update_replay_summary,
)


def write_replay_csv(path):
    rows = [
        ["2026-06-22 08:35:00", "ES", 50, 52, 49, 51, 100],
        ["2026-06-22 08:30:00", "NQ", 100, 102, 99, 101, 100],
        ["2026-06-22 08:30:00", "ES", 50, 51, 49, 50, 100],
        ["2026-06-22 08:35:00", "NQ", 101, 103, 100, 102, 100],
        ["2026-06-22 08:40:00", "NQ", 102, 104, 101, 103, 100],
        ["2026-06-22 08:40:00", "ES", 51, 53, 50, 52, 100],
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["timestamp", "symbol", "open", "high", "low", "close", "volume"])
        writer.writerows(rows)


def write_settings(path):
    path.write_text(
        """
symbols:
  primary: NQ
  comparison: ES
sessions:
  New York:
    start: "08:30"
    end: "11:00"
market_structure:
  swing_lookback: 1
  smt_swing_lookback: 3
  manipulation_lookback: 20
  deviation_levels: [2.0]
risk:
  max_stop_points:
    NQ: 15
deviations:
  tolerance_points:
    NQ: 5
momentum:
  body_shrink_lookback: 3
  body_shrink_ratio: 0.75
  rejection_wick_ratio: 1.5
  failed_continuation_bars: 2
scoring:
  manipulation_leg: 20
  price_at_deviation: 25
  smt_aligned: 25
  loss_of_momentum: 20
  target_liquidity_available: 10
  a_plus_threshold: 80
""".strip(),
        encoding="utf-8",
    )


def read_signal_rows(path):
    with path.open("r", newline="", encoding="utf-8") as signal_file:
        return list(csv.DictReader(signal_file))


def test_replay_loads_data_sorted_by_timestamp(tmp_path):
    csv_path = tmp_path / "candles.csv"
    write_replay_csv(csv_path)

    candles = load_replay_data(csv_path)

    assert list(candles["timestamp"]) == sorted(candles["timestamp"])


def test_replay_processes_candles_in_timestamp_order(tmp_path):
    csv_path = tmp_path / "candles.csv"
    write_replay_csv(csv_path)
    candles = load_replay_data(csv_path)

    timestamps = [timestamp for timestamp, _ in iter_replay_steps(candles)]

    assert timestamps == sorted(timestamps)
    assert timestamps[0] == pd.Timestamp("2026-06-22 08:30:00")


def test_replay_does_not_duplicate_logged_evaluations(tmp_path):
    csv_path = tmp_path / "candles.csv"
    settings_path = tmp_path / "settings.yaml"
    log_path = tmp_path / "logs" / "signals.csv"
    write_replay_csv(csv_path)
    write_settings(settings_path)

    run_replay(csv_path, settings_path, log_path, limit=2)
    first_rows = read_signal_rows(log_path)
    run_replay(csv_path, settings_path, log_path, limit=2)
    second_rows = read_signal_rows(log_path)

    assert len(first_rows) == 2
    assert len(second_rows) == 2


def test_replay_summary_counts_processed_candles_and_high_score(tmp_path):
    csv_path = tmp_path / "candles.csv"
    settings_path = tmp_path / "settings.yaml"
    log_path = tmp_path / "logs" / "signals.csv"
    write_replay_csv(csv_path)
    write_settings(settings_path)

    summary = run_replay(csv_path, settings_path, log_path, limit=2)

    assert summary["total_candles_processed"] == 4
    assert summary["highest_setup_score"] >= 0
    assert "alert_counts" in summary


def test_update_replay_summary_counts_meaningful_alerts_only_when_saved():
    summary = {
        "total_candles_processed": 0,
        "total_alerts_generated": 0,
        "alert_counts": {},
        "highest_setup_score": 0,
        "latest_alert": None,
    }

    update_replay_summary(
        summary,
        {
            "alert_state": "A_PLUS_SETUP",
            "setup_score": 90,
            "suggested_entry_direction": "bullish",
        },
        row_saved=True,
    )
    update_replay_summary(
        summary,
        {
            "alert_state": "A_PLUS_SETUP",
            "setup_score": 90,
            "suggested_entry_direction": "bullish",
        },
        row_saved=False,
    )

    assert summary["total_alerts_generated"] == 1
    assert summary["alert_counts"]["A_PLUS_SETUP"] == 1
    assert summary["highest_setup_score"] == 90
