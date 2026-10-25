import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.audit_historical_universe import build_historical_universe_audit


def _payload():
    return {
        "health": [
            {"source": "TWSE_BASIC", "ok": True, "parsed_events": 2},
            {"source": "TPEX_BASIC", "ok": True, "parsed_events": 1},
            {"source": "TWSE_DELIST", "ok": True, "parsed_events": 3},
            {"source": "TPEX_DELIST", "ok": True, "parsed_events": 2},
        ],
        "events": [
            {
                "symbol": "1111",
                "exchange": "TWSE",
                "name": "Old",
                "event_type": "LIST",
                "event_date": "2020-01-01",
                "source": "official_listing_api",
                "source_url": "u",
                "source_as_of": "2026-10-25",
                "notes": "",
            },
            {
                "symbol": "1111",
                "exchange": "TWSE",
                "name": "Old",
                "event_type": "DELIST",
                "event_date": "2024-06-30",
                "source": "official_delisting_page",
                "source_url": "u",
                "source_as_of": "2026-10-25",
                "notes": "",
            },
            {
                "symbol": "2222",
                "exchange": "TWSE",
                "name": "New",
                "event_type": "LIST",
                "event_date": "2025-01-01",
                "source": "official_listing_api",
                "source_url": "u",
                "source_as_of": "2026-10-25",
                "notes": "",
            },
            {
                "symbol": "3333",
                "exchange": "TPEx",
                "name": "Always",
                "event_type": "LIST",
                "event_date": "2020-01-01",
                "source": "official_listing_csv",
                "source_url": "u",
                "source_as_of": "2026-10-25",
                "notes": "",
            },
        ],
        "intervals": [
            {
                "symbol": "1111",
                "exchange": "TWSE",
                "name": "Old",
                "listed_from": "2020-01-01",
                "listed_to": "2024-06-30",
                "source": "official",
                "source_as_of": "2026-10-25",
            },
            {
                "symbol": "2222",
                "exchange": "TWSE",
                "name": "New",
                "listed_from": "2025-01-01",
                "listed_to": None,
                "source": "official",
                "source_as_of": "2026-10-25",
            },
            {
                "symbol": "3333",
                "exchange": "TPEx",
                "name": "Always",
                "listed_from": "2020-01-01",
                "listed_to": None,
                "source": "official",
                "source_as_of": "2026-10-25",
            },
        ],
        "unresolved": [],
    }


def test_audit_detects_survivorship_bias():
    current = [
        {"symbol": "2222", "exchange": "TWSE"},
        {"symbol": "3333", "exchange": "TPEx"},
    ]
    out = build_historical_universe_audit(
        official_payload=_payload(),
        current_universe=current,
        audit_dates=["2023-12-31"],
    )
    twse = out["historical_dates"]["2023-12-31"]["by_exchange"]["TWSE"]
    assert twse["historical_names_missing_from_current_n"] == 1
    assert twse["current_names_not_yet_listed_n"] == 1
    assert twse["survivorship_bias_present"] is True


def test_gate_passes_with_complete_current_interval_coverage():
    current = [
        {"symbol": "2222", "exchange": "TWSE"},
        {"symbol": "3333", "exchange": "TPEx"},
    ]
    out = build_historical_universe_audit(
        official_payload=_payload(),
        current_universe=current,
        audit_dates=["2025-12-31"],
    )
    assert out["historical_universe_gate_pass"] is True


def test_window_unresolved_event_blocks_gate():
    p = _payload()
    p["events"].extend([
        {
            "symbol": "9999",
            "exchange": "TWSE",
            "name": "Unknown",
            "event_type": "DELIST",
            "event_date": "2024-06-30",
            "source": "official_delisting_page",
            "source_url": "u",
            "source_as_of": "2026-10-25",
            "notes": "",
        },
        {
            "symbol": "9999",
            "exchange": "TWSE",
            "name": "Unknown",
            "event_type": "DELIST",
            "event_date": "2025-06-30",
            "source": "official_delisting_page",
            "source_url": "u",
            "source_as_of": "2026-10-25",
            "notes": "",
        },
    ])
    current = [
        {"symbol": "2222", "exchange": "TWSE"},
        {"symbol": "3333", "exchange": "TPEx"},
    ]
    out = build_historical_universe_audit(
        official_payload=p,
        current_universe=current,
        audit_dates=["2025-12-31"],
    )
    assert out["unresolved"] == 1
    assert out["historical_universe_gate_pass"] is False


def test_strict_pre_window_unresolved_does_not_block_window_gate():
    p = _payload()
    p["unresolved"] = [{"symbol": "9999", "reason": "PRE_WINDOW"}]
    current = [
        {"symbol": "2222", "exchange": "TWSE"},
        {"symbol": "3333", "exchange": "TPEx"},
    ]
    out = build_historical_universe_audit(
        official_payload=p,
        current_universe=current,
        audit_dates=["2025-12-31"],
    )
    assert out["strict_unresolved"] == 1
    assert out["unresolved"] == 0
    assert out["historical_universe_gate_pass"] is True


def test_source_failure_blocks_gate():
    p = _payload()
    p["health"][0]["ok"] = False
    current = [
        {"symbol": "2222", "exchange": "TWSE"},
        {"symbol": "3333", "exchange": "TPEx"},
    ]
    out = build_historical_universe_audit(
        official_payload=p,
        current_universe=current,
        audit_dates=["2025-12-31"],
    )
    assert out["historical_universe_gate_pass"] is False


def test_empty_historical_membership_blocks_gate():
    p = _payload()
    p["events"] = [
        {
            "symbol": "2222",
            "exchange": "TWSE",
            "name": "FutureOnly",
            "event_type": "LIST",
            "event_date": "2026-10-01",
            "source": "official_listing_api",
            "source_url": "u",
            "source_as_of": "2026-10-25",
            "notes": "",
        },
        {
            "symbol": "3333",
            "exchange": "TPEx",
            "name": "FutureOnly2",
            "event_type": "LIST",
            "event_date": "2026-10-01",
            "source": "official_listing_csv",
            "source_url": "u",
            "source_as_of": "2026-10-25",
            "notes": "",
        },
    ]
    p["intervals"] = []
    current = [
        {"symbol": "2222", "exchange": "TWSE"},
        {"symbol": "3333", "exchange": "TPEx"},
    ]
    out = build_historical_universe_audit(
        official_payload=p,
        current_universe=current,
        audit_dates=["2025-12-31"],
    )
    assert out["historical_dates_nonempty"] is False
    assert out["historical_universe_gate_pass"] is False

def test_missing_delisting_evidence_blocks_gate():
    p = _payload()
    for item in p["health"]:
        if item["source"] in {"TWSE_DELIST", "TPEX_DELIST"}:
            item["parsed_events"] = 0
    current = [
        {"symbol": "2222", "exchange": "TWSE"},
        {"symbol": "3333", "exchange": "TPEx"},
    ]
    out = build_historical_universe_audit(
        official_payload=p,
        current_universe=current,
        audit_dates=["2025-12-31"],
    )
    assert out["historical_source_coverage_ok"] is False
    assert out["historical_universe_gate_pass"] is False


def test_extraneous_open_interval_blocks_gate():
    p=_payload()
    p["events"].append({
        "symbol":"9998","exchange":"TPEx","name":"StaleManaged",
        "event_type":"LIST","event_date":"2020-01-01",
        "source":"official_basic_data","source_url":"u",
        "source_as_of":"2026-10-25","notes":"",
    })
    current=[
        {"symbol":"2222","exchange":"TWSE"},
        {"symbol":"3333","exchange":"TPEx"},
    ]
    out=build_historical_universe_audit(
        official_payload=p,
        current_universe=current,
        audit_dates=["2025-12-31"],
    )
    assert out["current_open_interval_alignment_ok"] is False
    assert out["current_interval_coverage"]["TPEx"]["extraneous_open_symbol_count"] == 1
    assert "9998" in out["current_interval_coverage"]["TPEx"]["extraneous_open_symbols"]
    assert out["historical_universe_gate_pass"] is False


def test_windowed_cross_exchange_migration_closes_prior_market():
    p=_payload()
    p["events"].extend([
        {
            "symbol":"4444","exchange":"TPEx","name":"Mover",
            "event_type":"LIST","event_date":"2020-01-01",
            "source":"official","source_url":"u","source_as_of":"2026-10-25","notes":"",
        },
        {
            "symbol":"4444","exchange":"TWSE","name":"Mover",
            "event_type":"LIST","event_date":"2025-02-03",
            "source":"official","source_url":"u","source_as_of":"2026-10-25","notes":"",
        },
    ])
    current=[
        {"symbol":"2222","exchange":"TWSE"},
        {"symbol":"3333","exchange":"TPEx"},
        {"symbol":"4444","exchange":"TWSE"},
    ]
    out=build_historical_universe_audit(
        official_payload=p,
        current_universe=current,
        audit_dates=["2025-12-31"],
    )
    assert out["current_open_interval_alignment_ok"] is True
    assert out["historical_universe_gate_pass"] is True
