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


def test_unresolved_event_blocks_gate():
    p = _payload()
    p["unresolved"] = [{"symbol": "9999"}]
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
    p["intervals"] = [
        {
            "symbol": "2222",
            "exchange": "TWSE",
            "name": "FutureOnly",
            "listed_from": "2026-10-01",
            "listed_to": None,
            "source": "official",
            "source_as_of": "2026-10-25",
        },
        {
            "symbol": "3333",
            "exchange": "TPEx",
            "name": "FutureOnly2",
            "listed_from": "2026-10-01",
            "listed_to": None,
            "source": "official",
            "source_as_of": "2026-10-25",
        },
    ]
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
