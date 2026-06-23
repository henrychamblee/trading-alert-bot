"""Configurable session tagging helpers."""

from datetime import time

import pandas as pd


SESSION_WINDOWS = {
    "Asia": (time(20, 0), time(0, 0)),
    "London": (time(2, 0), time(5, 0)),
    "New York": (time(8, 30), time(11, 0)),
    "Lunch": (time(11, 0), time(13, 30)),
    "New York PM": (time(13, 30), time(16, 0)),
}


def parse_session_time(value: str) -> time:
    """Parse a HH:MM session time string."""
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def build_session_windows(settings: dict | None = None) -> dict[str, tuple[time, time]]:
    """Build session windows from settings, falling back to defaults."""
    session_settings = (settings or {}).get("sessions")
    if not session_settings:
        return SESSION_WINDOWS

    return {
        session_name: (
            parse_session_time(window["start"]),
            parse_session_time(window["end"]),
        )
        for session_name, window in session_settings.items()
    }


def is_time_in_window(value: time, start: time, end: time) -> bool:
    """Return True when a time falls inside a session window."""
    if start <= end:
        return start <= value < end
    return value >= start or value < end


def get_session(
    timestamp: pd.Timestamp,
    session_windows: dict[str, tuple[time, time]] | None = None,
) -> str:
    """Label a timestamp with a trading session name or off_session."""
    current_time = timestamp.time()
    for session_name, (start, end) in (session_windows or SESSION_WINDOWS).items():
        if is_time_in_window(current_time, start, end):
            return session_name
    return "off_session"


def tag_sessions(
    candles: pd.DataFrame,
    session_windows: dict[str, tuple[time, time]] | None = None,
) -> pd.DataFrame:
    """Add a session column to a candle DataFrame."""
    tagged = candles.copy()
    tagged["session"] = tagged["timestamp"].apply(
        lambda timestamp: get_session(timestamp, session_windows)
    )
    return tagged
