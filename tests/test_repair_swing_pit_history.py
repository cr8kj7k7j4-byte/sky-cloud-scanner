import json

from research.repair_swing_pit_history import _rewrite_with_fresh_pit


def test_repair_reassigns_exchange_from_fresh_pit():
    payload = {
        "symbol": "1597",
        "adjustment_capability": "PIT_ASOF_EVENT_LEDGER",
        "data": [
            {
                "date": "2023-01-03",
                "exchange": "TPEx",
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10,
                "volume": 1,
            }
        ],
    }
    intervals = [
        {
            "symbol": "1597",
            "exchange": "TWSE",
            "listed_from": "2023-01-01",
            "listed_to": None,
        }
    ]
    out, stats = _rewrite_with_fresh_pit(payload, intervals)
    assert out["data"][0]["exchange"] == "TWSE"
    assert out["data"][0]["pit_reconciled"] is True
    assert stats["ambiguous_rows"] == 0


def test_repair_fails_closed_on_ambiguous_fresh_pit():
    payload = {
        "symbol": "4444",
        "adjustment_capability": "PIT_ASOF_EVENT_LEDGER",
        "data": [
            {
                "date": "2024-01-02",
                "exchange": "TPEx",
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10,
                "volume": 1,
            }
        ],
    }
    intervals = [
        {
            "symbol": "4444",
            "exchange": "TPEx",
            "listed_from": "2023-01-01",
            "listed_to": None,
        },
        {
            "symbol": "4444",
            "exchange": "TWSE",
            "listed_from": "2023-01-01",
            "listed_to": None,
        },
    ]
    try:
        _rewrite_with_fresh_pit(payload, intervals)
        assert False, "expected ambiguous mapping failure"
    except ValueError as exc:
        assert "ambiguous" in str(exc)
