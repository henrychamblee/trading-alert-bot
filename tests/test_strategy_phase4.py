from src.strategy import determine_alert_state, score_setup


def test_score_setup_reaches_100_when_all_conditions_pass():
    result = score_setup(
        {"detected": True},
        {"within_tolerance": True},
        {"detected": True},
        {"detected": True},
        True,
    )

    assert result["score"] == 100


def test_determine_alert_state_returns_entry_alert_for_a_plus_with_momentum():
    state = determine_alert_state(
        90,
        "bullish",
        {"within_tolerance": True},
        {"detected": True},
        a_plus_threshold=85,
    )

    assert state == "ENTRY_ALERT"


def test_entry_alert_requires_ote_or_sweep_confirmation():
    state = determine_alert_state(
        90,
        "bullish",
        {"within_tolerance": True},
        {"detected": True},
        {"detected": True},
        {
            "ote_touched": False,
            "sweep_confirmed": False,
            "displacement_confirmed": True,
        },
        a_plus_threshold=80,
    )

    assert state == "A_PLUS_SETUP"


def test_entry_alert_can_require_displacement_from_config():
    state = determine_alert_state(
        90,
        "bullish",
        {"within_tolerance": True},
        {"detected": True},
        {"detected": True},
        {
            "ote_touched": True,
            "sweep_confirmed": False,
            "displacement_confirmed": False,
        },
        entry_requires_displacement=True,
        a_plus_threshold=80,
    )

    assert state == "A_PLUS_SETUP"


def test_entry_alert_triggers_with_score_smt_deviation_momentum_and_ote():
    state = determine_alert_state(
        90,
        "bullish",
        {"within_tolerance": True},
        {"detected": True},
        {"detected": True},
        {
            "ote_touched": True,
            "sweep_confirmed": False,
            "displacement_confirmed": False,
        },
        entry_requires_displacement=False,
        a_plus_threshold=80,
    )

    assert state == "ENTRY_ALERT"


def test_determine_alert_state_returns_no_setup_without_direction():
    state = determine_alert_state(
        90,
        None,
        {"within_tolerance": True},
        {"detected": True},
    )

    assert state == "NO_SETUP"


def test_determine_alert_state_returns_invalidated_when_stop_is_breached():
    state = determine_alert_state(
        100,
        "bearish",
        {"within_tolerance": True},
        {"detected": True},
        invalidated=True,
    )

    assert state == "INVALIDATED"
