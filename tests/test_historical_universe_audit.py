import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.audit_historical_universe import build_historical_universe_audit


def _payload():
    return {
        "health": [
            {"source": "TWSE_BASIC", "ok": True},
            {"source": "TPEX_BASIC", "ok": True},
            {"source": "TWSE_DELIST", "ok": True},
            {"source": "TPEX_DELIST", "ok": True},
        ],
        "events": [{"x": 1}],
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
