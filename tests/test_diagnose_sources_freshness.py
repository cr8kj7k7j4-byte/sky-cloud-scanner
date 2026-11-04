from datetime import datetime
from zoneinfo import ZoneInfo

from src import diagnose_sources


def test_quote_access_with_no_current_trade_is_not_marked_ok(monkeypatch):
    monkeypatch.setattr(diagnose_sources, "get_quote", lambda symbol: {
        "data": {"date": "2026-11-03", "lastPrice": 30,
                 "lastTrade": {"price": 30, "time": 1793650000000}}
    })
    result = diagnose_sources._probe_executed_quote("2330")
    assert result["ok"] is False
    assert result["api_accessible"] is True
    assert result["fresh_executed_trade"] is False


def test_quote_access_without_valid_payload_does_not_mark_available(monkeypatch):
    monkeypatch.setattr(diagnose_sources, "get_quote", lambda symbol: {"data": []})
    result = diagnose_sources._probe_executed_quote("8089")
    assert result["ok"] is False
    assert result["status"] == "INVALID_QUOTE_PAYLOAD"


def test_plan_restricted_is_distinct_from_stale_quote(monkeypatch):
    def denied(symbol):
        raise PermissionError("entitlement missing")
    monkeypatch.setattr(diagnose_sources, "get_quote", denied)
    result = diagnose_sources._probe_executed_quote("2330")
    assert result["status"] == "PLAN_RESTRICTED"
    assert result["api_accessible"] is False
