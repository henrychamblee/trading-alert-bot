"""Logging helpers used across the alert assistant."""

import csv
import logging
from pathlib import Path


SIGNAL_COLUMNS = [
    "timestamp",
    "symbol",
    "current_session",
    "alert_state",
    "setup_score",
    "suggested_direction",
    "latest_smt_type",
    "latest_smt_mode",
    "smt_timestamp",
    "smt_level",
    "manipulation_start",
    "manipulation_end",
    "manipulation_direction",
    "nearest_deviation_level",
    "nearest_deviation_price",
    "nearest_deviation_direction",
    "stop_loss",
    "take_profit_primary",
    "take_profit_secondary",
    "notes",
]


def get_logger(name: str = "trading_alert_bot") -> logging.Logger:
    """Return a configured console logger."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return logging.getLogger(name)


def _stringify(value) -> str:
    """Convert values to CSV-friendly strings while keeping blanks readable."""
    if value is None:
        return ""
    return str(value)


def build_signal_row(
    latest_candle,
    symbol: str,
    smt_result: dict,
    manipulation_leg: dict,
    setup_snapshot: dict,
    notes: str = "",
) -> dict:
    """Build one signal-log row from the current strategy evaluation."""
    nearest_deviation = setup_snapshot.get("nearest_deviation", {})
    take_profit = setup_snapshot.get("take_profit", {})
    secondary_targets = take_profit.get("secondary", [])
    secondary_text = "; ".join(
        f"{target.get('name')}={target.get('price')}" for target in secondary_targets
    )

    row = {
        "timestamp": latest_candle["timestamp"],
        "symbol": symbol,
        "current_session": latest_candle.get("session"),
        "alert_state": setup_snapshot.get("alert_state"),
        "setup_score": setup_snapshot.get("setup_score"),
        "suggested_direction": setup_snapshot.get("suggested_entry_direction"),
        "latest_smt_type": smt_result.get("smt_type"),
        "latest_smt_mode": smt_result.get("smt_mode"),
        "smt_timestamp": smt_result.get("smt_timestamp"),
        "smt_level": smt_result.get("smt_level"),
        "manipulation_start": manipulation_leg.get("manipulation_start"),
        "manipulation_end": manipulation_leg.get("manipulation_end"),
        "manipulation_direction": manipulation_leg.get("manipulation_direction"),
        "nearest_deviation_level": nearest_deviation.get("deviation_level"),
        "nearest_deviation_price": nearest_deviation.get("deviation_price"),
        "nearest_deviation_direction": nearest_deviation.get("deviation_direction"),
        "stop_loss": setup_snapshot.get("stop_loss"),
        "take_profit_primary": take_profit.get("primary"),
        "take_profit_secondary": secondary_text,
        "notes": notes,
    }
    return {column: _stringify(row.get(column)) for column in SIGNAL_COLUMNS}


def _is_duplicate_signal(existing_row: dict, new_row: dict) -> bool:
    """Return True when a signal already exists for the same candle setup."""
    duplicate_keys = [
        "timestamp",
        "alert_state",
        "suggested_direction",
        "nearest_deviation_level",
    ]
    return all(existing_row.get(key, "") == new_row.get(key, "") for key in duplicate_keys)


def append_signal_row(log_path: str | Path, row: dict) -> bool:
    """Append a signal row unless the same candle setup was already logged."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_row = {column: _stringify(row.get(column)) for column in SIGNAL_COLUMNS}

    if log_path.exists():
        with log_path.open("r", newline="", encoding="utf-8") as signal_file:
            reader = csv.DictReader(signal_file)
            for existing_row in reader:
                if _is_duplicate_signal(existing_row, normalized_row):
                    return False

    write_header = not log_path.exists() or log_path.stat().st_size == 0
    with log_path.open("a", newline="", encoding="utf-8") as signal_file:
        writer = csv.DictWriter(signal_file, fieldnames=SIGNAL_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(normalized_row)
    return True


def review_signal_log(log_path: str | Path) -> dict:
    """Summarize the signal log for review mode."""
    log_path = Path(log_path)
    if not log_path.exists():
        return {"exists": False}

    with log_path.open("r", newline="", encoding="utf-8") as signal_file:
        rows = list(csv.DictReader(signal_file))

    alert_counts = {}
    scores = []
    for row in rows:
        alert_state = row.get("alert_state", "")
        alert_counts[alert_state] = alert_counts.get(alert_state, 0) + 1
        try:
            scores.append(float(row.get("setup_score", 0)))
        except ValueError:
            pass

    average_score = sum(scores) / len(scores) if scores else 0
    return {
        "exists": True,
        "total_alerts": len(rows),
        "alert_counts": alert_counts,
        "latest_alerts": rows[-10:],
        "average_setup_score": average_score,
    }


def print_review_summary(summary: dict) -> None:
    """Print a readable signal-log review summary."""
    if not summary.get("exists"):
        print("No signal log found yet.")
        return

    print("\nSignal Review")
    print("-------------")
    print(f"Total alerts: {summary['total_alerts']}")
    print("Alerts by state:")
    for alert_state, count in sorted(summary["alert_counts"].items()):
        print(f"{alert_state}: {count}")
    print(f"Average setup_score: {summary['average_setup_score']:.2f}")
    print("Latest 10 alerts:")
    for row in summary["latest_alerts"]:
        print(
            f"{row.get('timestamp')} | {row.get('symbol')} | "
            f"{row.get('alert_state')} | score={row.get('setup_score')} | "
            f"direction={row.get('suggested_direction')}"
        )
