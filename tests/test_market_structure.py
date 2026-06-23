import pandas as pd

from src.data_loader import add_midnight_open, add_previous_day_levels, enrich_market_structure


def test_add_midnight_open_stores_daily_open_by_symbol():
    candles = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-06-22 00:00:00",
                    "2026-06-22 08:30:00",
                    "2026-06-22 00:00:00",
                    "2026-06-22 08:30:00",
                ]
            ),
            "symbol": ["NQ", "NQ", "ES", "ES"],
            "open": [100, 105, 50, 52],
            "high": [101, 108, 51, 53],
            "low": [99, 104, 49, 51],
            "close": [100, 106, 50, 52],
            "volume": [1, 1, 1, 1],
        }
    )

    enriched = add_midnight_open(candles)

    assert enriched[enriched["symbol"] == "NQ"].iloc[-1]["midnight_open"] == 100
    assert enriched[enriched["symbol"] == "ES"].iloc[-1]["midnight_open"] == 50


def test_add_previous_day_levels_adds_pdh_and_pdl_by_symbol():
    candles = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-06-21 08:30:00",
                    "2026-06-21 09:00:00",
                    "2026-06-22 08:30:00",
                    "2026-06-21 08:30:00",
                    "2026-06-22 08:30:00",
                ]
            ),
            "symbol": ["NQ", "NQ", "NQ", "ES", "ES"],
            "open": [1, 1, 1, 1, 1],
            "high": [100, 110, 120, 50, 60],
            "low": [90, 95, 115, 45, 55],
            "close": [1, 1, 1, 1, 1],
            "volume": [1, 1, 1, 1, 1],
        }
    )

    enriched = add_previous_day_levels(candles)
    nq_latest = enriched[(enriched["symbol"] == "NQ") & (enriched["timestamp"].dt.date == pd.Timestamp("2026-06-22").date())].iloc[0]
    es_latest = enriched[(enriched["symbol"] == "ES") & (enriched["timestamp"].dt.date == pd.Timestamp("2026-06-22").date())].iloc[0]

    assert nq_latest["pdh"] == 110
    assert nq_latest["pdl"] == 90
    assert es_latest["pdh"] == 50
    assert es_latest["pdl"] == 45


def test_enrich_market_structure_adds_expected_columns():
    candles = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-22 00:00:00"]),
            "symbol": ["NQ"],
            "open": [100],
            "high": [101],
            "low": [99],
            "close": [100],
            "volume": [1],
        }
    )

    enriched = enrich_market_structure(candles)

    assert {"trading_day", "midnight_open", "pdh", "pdl"}.issubset(enriched.columns)
