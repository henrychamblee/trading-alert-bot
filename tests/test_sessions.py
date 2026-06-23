import pandas as pd

from src.sessions import build_session_windows, get_session, tag_sessions


def test_get_session_identifies_new_york():
    timestamp = pd.Timestamp("2026-06-22 08:45:00")

    assert get_session(timestamp) == "New York"


def test_get_session_identifies_asia_across_midnight():
    timestamp = pd.Timestamp("2026-06-22 23:30:00")

    assert get_session(timestamp) == "Asia"


def test_get_session_returns_off_session():
    timestamp = pd.Timestamp("2026-06-22 17:00:00")

    assert get_session(timestamp) == "off_session"


def test_get_session_identifies_lunch_and_new_york_pm():
    assert get_session(pd.Timestamp("2026-06-22 11:30:00")) == "Lunch"
    assert get_session(pd.Timestamp("2026-06-22 14:00:00")) == "New York PM"


def test_tag_sessions_uses_configurable_windows():
    settings = {
        "sessions": {
            "Custom Morning": {"start": "07:00", "end": "09:00"},
        }
    }
    windows = build_session_windows(settings)
    candles = pd.DataFrame({"timestamp": [pd.Timestamp("2026-06-22 08:00:00")]})

    tagged = tag_sessions(candles, windows)

    assert tagged.iloc[0]["session"] == "Custom Morning"
