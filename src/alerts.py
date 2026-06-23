"""Alert formatting and delivery placeholders.

Only console alerts are implemented. Broker execution is intentionally absent.
"""


def format_alert(title: str, details: dict) -> str:
    """Build a readable alert message."""
    detail_lines = [f"{key}: {value}" for key, value in details.items()]
    return "\n".join([f"ALERT: {title}", *detail_lines])


def send_console_alert(message: str) -> None:
    """Print an alert to the terminal."""
    print(message)


def format_setup_alert(snapshot: dict) -> str:
    """Build a concise alert-state message from a setup snapshot."""
    return format_alert(
        snapshot.get("alert_state", "NO_SETUP"),
        {
            "score": snapshot.get("setup_score"),
            "direction": snapshot.get("suggested_entry_direction"),
            "stop_loss": snapshot.get("stop_loss"),
            "take_profit": snapshot.get("take_profit", {}).get("primary"),
        },
    )
