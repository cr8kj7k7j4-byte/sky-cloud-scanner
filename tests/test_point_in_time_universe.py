from src.point_in_time_universe import (
    validate_intervals,
    universe_as_of,
    survivorship_audit,
)

ROWS = [
    {
        "symbol": "1111", "exchange": "TWSE", "name": "OldCo",
        "listed_from": "2020-01-01", "listed_to": "2025-06-30",
        "source": "official"
    },
    {
        "symbol": "2222", "exchange": "TWSE", "name": "NewCo",
        "listed_from": "2026-01-15", "listed_to": None,
        "source": "official"
    },
    {
        "symbol": "3333", "exchange": "TPEx", "name": "AlwaysCo",
        "listed_from": "2019-01-01", "listed_to": None,
        "source": "official"
    },
]

def test_interval_contract_valid():
    out = validate_intervals(ROWS)
    assert out["valid"] is True
    assert out["rows"] == 3

def test_universe_is_date_correct():
    u2025 = {x["symbol"] for x in universe_as_of(ROWS, "2025-03-01")}
    assert u2025 == {"1111", "3333"}

    u2026 = {x["symbol"] for x in universe_as_of(ROWS, "2026-03-01")}
    assert u2026 == {"2222", "3333"}

def test_delisted_name_is_kept_in_historical_universe():
    u = {x["symbol"] for x in universe_as_of(ROWS, "2025-03-01")}
    assert "1111" in u

def test_future_listing_is_excluded():
    u = {x["symbol"] for x in universe_as_of(ROWS, "2025-03-01")}
    assert "2222" not in u

def test_survivorship_audit_detects_current_universe_bias():
    out = survivorship_audit(
        current_symbols={"2222", "3333"},
        pit_symbols={"1111", "3333"},
    )
    assert out["survivorship_bias_present"] is True
    assert out["historical_names_missing_from_current_universe"] == ["1111"]
    assert out["current_names_not_in_historical_universe"] == ["2222"]

def test_overlapping_same_exchange_intervals_fail():
    bad = ROWS + [{
        "symbol": "1111", "exchange": "TWSE", "name": "OldCo",
        "listed_from": "2025-01-01", "listed_to": "2025-12-31",
        "source": "official",
    }]
    out = validate_intervals(bad)
    assert out["valid"] is False
    assert any(x.startswith("overlap:1111") for x in out["errors"])
