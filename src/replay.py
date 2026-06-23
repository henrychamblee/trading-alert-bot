"""Candle-by-candle replay engine for historical NQ and ES data."""

from pathlib import Path
import time

import pandas as pd

from data_loader import enrich_market_structure, load_candles, load_settings
from deviations import detect_manipulation_leg
from logger import append_signal_row, build_signal_row
from sessions import build_session_windows, tag_sessions
from smt import detect_smt_divergence
from strategy import build_setup_snapshot
from swings import tag_swings


MEANINGFUL_STATES = {"SETUP_FORMING", "A_PLUS_SETUP", "ENTRY_ALERT", "INVALIDATED"}


def load_replay_data(csv_path: str | Path) -> pd.DataFrame:
    """Load and sort historical candles for replay."""
    return load_candles(csv_path).sort_values(["timestamp", "symbol"]).reset_index(drop=True)


def iter_replay_steps(candles: pd.DataFrame, limit: int | None = None):
    """Yield accumulated candles one timestamp at a time."""
    timestamps = sorted(candles["timestamp"].unique())
    if limit is not None:
        timestamps = timestamps[:limit]

    for timestamp in timestamps:
        yield timestamp, candles[candles["timestamp"] <= timestamp].copy()


def evaluate_replay_step(
    candles: pd.DataFrame,
    settings: dict,
    primary_symbol: str = "NQ",
    comparison_symbol: str = "ES",
) -> dict:
    """Evaluate the existing alert-only strategy at one replay step."""
    session_windows = build_session_windows(settings)
    market_settings = settings.get("market_structure", {})
    swing_lookback = market_settings.get("swing_lookback", 1)
    smt_lookback = market_settings.get("smt_swing_lookback", 3)
    manipulation_lookback = market_settings.get("manipulation_lookback", 20)

    enriched = tag_sessions(candles, session_windows)
    enriched = enrich_market_structure(enriched)
    enriched = tag_swings(enriched, swing_lookback)

    primary_candles = enriched[enriched["symbol"] == primary_symbol]
    comparison_candles = enriched[enriched["symbol"] == comparison_symbol]
    smt_result = detect_smt_divergence(primary_candles, comparison_candles, smt_lookback)
    manipulation_leg = detect_manipulation_leg(
        enriched,
        smt_result,
        primary_symbol,
        manipulation_lookback,
    )
    setup_snapshot = build_setup_snapshot(
        enriched,
        smt_result,
        manipulation_leg,
        settings,
        primary_symbol,
    )

    latest_primary = primary_candles.sort_values("timestamp").iloc[-1]
    return {
        "candles": enriched,
        "latest_candle": latest_primary,
        "smt_result": smt_result,
        "manipulation_leg": manipulation_leg,
        "setup_snapshot": setup_snapshot,
    }


def _empty_summary() -> dict:
    """Return an initialized replay summary."""
    return {
        "total_candles_processed": 0,
        "total_alerts_generated": 0,
        "alert_counts": {},
        "highest_setup_score": 0,
        "latest_alert": None,
    }


def update_replay_summary(summary: dict, setup_snapshot: dict, row_saved: bool) -> dict:
    """Update replay summary stats from one evaluated setup."""
    alert_state = setup_snapshot.get("alert_state", "NO_SETUP")
    score = setup_snapshot.get("setup_score", 0) or 0
    summary["highest_setup_score"] = max(summary["highest_setup_score"], score)

    if row_saved and alert_state in MEANINGFUL_STATES:
        summary["total_alerts_generated"] += 1
        summary["alert_counts"][alert_state] = summary["alert_counts"].get(alert_state, 0) + 1
        summary["latest_alert"] = {
            "alert_state": alert_state,
            "setup_score": score,
            "suggested_direction": setup_snapshot.get("suggested_entry_direction"),
        }

    return summary


def should_print_replay_state(setup_snapshot: dict, verbose: bool = False) -> bool:
    """Return True when replay should print this step."""
    alert_state = setup_snapshot.get("alert_state", "NO_SETUP")
    return verbose or alert_state in MEANINGFUL_STATES


def print_replay_state(timestamp, setup_snapshot: dict) -> None:
    """Print one meaningful replay state."""
    entry_refinement = setup_snapshot.get("entry_refinement", {})
    print(
        f"{timestamp} | {setup_snapshot.get('alert_state')} | "
        f"score={setup_snapshot.get('setup_score')} | "
        f"direction={setup_snapshot.get('suggested_entry_direction')} | "
        f"OTE={entry_refinement.get('ote_touched')} | "
        f"sweep={entry_refinement.get('sweep_confirmed')} | "
        f"displacement={entry_refinement.get('displacement_confirmed')} | "
        f"FVG={entry_refinement.get('fvg_type')} | "
        f"reason={setup_snapshot.get('entry_trigger_reason')}"
    )


def print_replay_summary(summary: dict) -> None:
    """Print final replay statistics."""
    print("\nReplay Summary")
    print("--------------")
    print(f"Total candles processed: {summary['total_candles_processed']}")
    print(f"Total alerts generated: {summary['total_alerts_generated']}")
    print("Alert counts by state:")
    if summary["alert_counts"]:
        for alert_state, count in sorted(summary["alert_counts"].items()):
            print(f"{alert_state}: {count}")
    else:
        print("None")
    print(f"Highest setup score: {summary['highest_setup_score']}")
    print(f"Latest alert: {summary['latest_alert']}")


def run_replay(
    csv_path: str | Path,
    settings_path: str | Path,
    signal_log_path: str | Path,
    speed: float = 0,
    limit: int | None = None,
    verbose: bool = False,
) -> dict:
    """Replay historical candles and log each strategy evaluation."""
    settings = load_settings(settings_path)
    symbols = settings.get("symbols", {})
    primary_symbol = symbols.get("primary", "NQ")
    comparison_symbol = symbols.get("comparison", "ES")
    candles = load_replay_data(csv_path)
    summary = _empty_summary()

    for timestamp, replay_candles in iter_replay_steps(candles, limit):
        if primary_symbol not in set(replay_candles["symbol"]):
            continue

        evaluation = evaluate_replay_step(
            replay_candles,
            settings,
            primary_symbol,
            comparison_symbol,
        )
        setup_snapshot = evaluation["setup_snapshot"]
        signal_row = build_signal_row(
            evaluation["latest_candle"],
            primary_symbol,
            evaluation["smt_result"],
            evaluation["manipulation_leg"],
            setup_snapshot,
            notes="Replay evaluation",
        )
        row_saved = append_signal_row(signal_log_path, signal_row)
        summary["total_candles_processed"] += len(
            replay_candles[replay_candles["timestamp"] == timestamp]
        )
        update_replay_summary(summary, setup_snapshot, row_saved)

        if should_print_replay_state(setup_snapshot, verbose):
            print_replay_state(timestamp, setup_snapshot)

        if speed > 0:
            time.sleep(speed)

    print_replay_summary(summary)
    return summary
