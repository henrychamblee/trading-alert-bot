"""Command-line entry point for the trading alert assistant."""

import argparse
from pathlib import Path
import sys

try:
    from logger import (
        append_signal_row,
        build_signal_row,
        get_logger,
        print_review_summary,
        review_signal_log,
    )
except ModuleNotFoundError as error:
    missing_package = error.name
    print(
        f"Missing dependency: {missing_package}. "
        "Install requirements or activate the project environment, then run again."
    )
    sys.exit(1)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA_PATH = PROJECT_ROOT / "data" / "sample_candles.csv"
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"
SIGNAL_LOG_PATH = PROJECT_ROOT / "logs" / "signals.csv"


def print_market_structure_summary(
    candles,
    smt_result: dict,
    manipulation_leg: dict,
    setup_snapshot: dict,
) -> None:
    """Print a clear Phase 4 snapshot from enriched candles."""
    latest = candles.sort_values("timestamp").iloc[-1]
    latest_swings = candles[candles["is_swing_high"] | candles["is_swing_low"]].tail(6)
    nearest_deviation = setup_snapshot.get("nearest_deviation", {})
    entry_refinement = setup_snapshot.get("entry_refinement", {})
    alert_state = setup_snapshot.get("alert_state", "NO_SETUP")

    print("\nPhase 4 Summary")
    print("---------------")
    print(f"Current session: {latest['session']}")
    print(f"Midnight open: {latest['midnight_open']}")
    print(f"PDH/PDL: {latest['pdh']} / {latest['pdl']}")
    print(f"Latest SMT: {smt_result.get('smt_type') or 'none'}")
    print(f"SMT mode: {smt_result.get('smt_mode') or 'none'}")
    print(f"SMT timestamp: {smt_result.get('smt_timestamp')}")
    print(f"SMT level: {smt_result.get('smt_level')}")
    print(
        "Manipulation leg: "
        f"{manipulation_leg.get('manipulation_start')} -> "
        f"{manipulation_leg.get('manipulation_end')}"
    )
    print(f"Manipulation direction: {manipulation_leg.get('manipulation_direction')}")
    print(
        "Nearest deviation: "
        f"level={nearest_deviation.get('deviation_level')}, "
        f"price={nearest_deviation.get('deviation_price')}, "
        f"direction={nearest_deviation.get('deviation_direction')}"
    )
    print(f"Setup score: {setup_snapshot.get('setup_score')}")
    print(f"Alert state: {alert_state}")
    print(f"Suggested direction: {setup_snapshot.get('suggested_entry_direction')}")
    print(
        "OTE zone: "
        f"{entry_refinement.get('ote_zone_low')} - "
        f"{entry_refinement.get('ote_zone_high')}"
    )
    print(f"OTE touched: {entry_refinement.get('ote_touched')}")
    print(
        "Sweep confirmation: "
        f"confirmed={entry_refinement.get('sweep_confirmed')}, "
        f"type={entry_refinement.get('sweep_type')}, "
        f"level={entry_refinement.get('sweep_level')}"
    )
    print(
        "Displacement confirmation: "
        f"confirmed={entry_refinement.get('displacement_confirmed')}, "
        f"timestamp={entry_refinement.get('displacement_timestamp')}"
    )
    print(
        "FVG details: "
        f"detected={entry_refinement.get('fvg_detected')}, "
        f"type={entry_refinement.get('fvg_type')}, "
        f"low={entry_refinement.get('fvg_low')}, "
        f"high={entry_refinement.get('fvg_high')}"
    )
    print(f"Final entry trigger reason: {setup_snapshot.get('entry_trigger_reason')}")
    print(f"Stop loss: {setup_snapshot.get('stop_loss')}")
    print(f"Take profit: {setup_snapshot.get('take_profit')}")

    if alert_state == "NO_SETUP":
        print("No setup found from sample data.")

    print("Latest swing highs/lows:")

    if latest_swings.empty:
        print("No confirmed swings yet.")
        return

    for _, swing in latest_swings.iterrows():
        swing_type = "high" if swing["is_swing_high"] else "low"
        swing_price = swing["high"] if swing["is_swing_high"] else swing["low"]
        print(
            f"{swing['timestamp']} | {swing['symbol']} | swing {swing_type}: {swing_price}"
        )


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="Trading alert bot")
    parser.add_argument(
        "--review",
        action="store_true",
        help="Review saved signal alerts instead of running a new evaluation.",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Replay historical candle data one timestamp at a time.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=0,
        help="Seconds to wait between replay timestamps.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of replay timestamps to process.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every replay state, including NO_SETUP.",
    )
    return parser.parse_args()


def run_review_mode() -> None:
    """Read the signal log and print review statistics."""
    summary = review_signal_log(SIGNAL_LOG_PATH)
    print_review_summary(summary)


def run_replay_mode(speed: float = 0, limit: int | None = None, verbose: bool = False) -> None:
    """Replay sample historical candles and save evaluations."""
    try:
        from replay import run_replay
    except ModuleNotFoundError as error:
        missing_package = error.name
        print(
            f"Missing dependency: {missing_package}. "
            "Install requirements or activate the project environment, then run again."
        )
        sys.exit(1)

    run_replay(
        SAMPLE_DATA_PATH,
        SETTINGS_PATH,
        SIGNAL_LOG_PATH,
        speed=speed,
        limit=limit,
        verbose=verbose,
    )


def run_normal_mode() -> None:
    """Load sample candles, evaluate alert-only logic, and print a summary."""
    try:
        from alerts import send_console_alert
        from data_loader import enrich_market_structure, load_candles, load_settings
        from deviations import detect_manipulation_leg
        from sessions import build_session_windows, tag_sessions
        from smt import detect_smt_divergence
        from strategy import build_setup_snapshot, evaluate_market
        from swings import tag_swings
    except ModuleNotFoundError as error:
        missing_package = error.name
        print(
            f"Missing dependency: {missing_package}. "
            "Install requirements or activate the project environment, then run again."
        )
        sys.exit(1)

    logger = get_logger()
    logger.info("Starting alert-only trading assistant")

    settings = load_settings(SETTINGS_PATH)
    session_windows = build_session_windows(settings)
    swing_lookback = settings.get("market_structure", {}).get("swing_lookback", 1)
    smt_lookback = settings.get("market_structure", {}).get("smt_swing_lookback", 3)
    manipulation_lookback = settings.get("market_structure", {}).get(
        "manipulation_lookback", 20
    )
    primary_symbol = settings.get("symbols", {}).get("primary", "NQ")
    comparison_symbol = settings.get("symbols", {}).get("comparison", "ES")

    candles = load_candles(SAMPLE_DATA_PATH)
    candles = tag_sessions(candles, session_windows)
    candles = enrich_market_structure(candles)
    candles = tag_swings(candles, swing_lookback)
    smt_result = detect_smt_divergence(
        candles[candles["symbol"] == primary_symbol],
        candles[candles["symbol"] == comparison_symbol],
        smt_lookback,
    )
    manipulation_leg = detect_manipulation_leg(
        candles,
        smt_result,
        primary_symbol,
        manipulation_lookback,
    )
    setup_snapshot = build_setup_snapshot(
        candles,
        smt_result,
        manipulation_leg,
        settings,
        primary_symbol,
    )
    print_market_structure_summary(candles, smt_result, manipulation_leg, setup_snapshot)

    latest_candle = (
        candles[candles["symbol"] == primary_symbol].sort_values("timestamp").iloc[-1]
    )
    signal_row = build_signal_row(
        latest_candle,
        primary_symbol,
        smt_result,
        manipulation_leg,
        setup_snapshot,
        notes="Sample data evaluation",
    )
    row_saved = append_signal_row(SIGNAL_LOG_PATH, signal_row)
    if row_saved:
        print(f"Signal log saved to: {SIGNAL_LOG_PATH}")
    else:
        print(f"Signal already logged for this candle: {SIGNAL_LOG_PATH}")

    alerts = evaluate_market(candles)

    if not alerts:
        print("No alerts generated from sample data.")
        return

    for alert in alerts:
        send_console_alert(alert)


def main() -> None:
    """Run normal evaluation or review saved signal logs."""
    args = parse_args()
    if args.review:
        run_review_mode()
        return
    if args.replay:
        run_replay_mode(args.speed, args.limit, args.verbose)
        return

    run_normal_mode()


if __name__ == "__main__":
    main()
