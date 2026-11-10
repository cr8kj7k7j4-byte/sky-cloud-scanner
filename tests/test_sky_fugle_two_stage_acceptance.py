from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from research.sky_fugle_two_stage_acceptance import (
    snapshot_audit, audit_individual, choose_samples, error_category
)

NOW = datetime(2026, 11, 10, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))


def payload(market, symbol):
    return {"date": NOW.date().isoformat(), "data": [
        {"symbol": symbol, "lastPrice": 40.0, "tradeVolume": 1000, "isTrial": False}
    ]}


def test_snapshot_two_markets_keep_reference_only():
    reports, raw = snapshot_audit(lambda m: payload(m, "2330" if m == "TSE" else "8299"), NOW)
    assert set(reports) == {"TSE", "OTC"}
    assert all(v["request_status"] == "OK" and v["same_date"] for v in reports.values())
    assert all(v["has_per_symbol_execution_time"] == 0 for v in reports.values())
    assert len(choose_samples(raw)) == 2


def test_individual_verified_only_with_trade_time():
    _, raw = snapshot_audit(lambda m: payload(m, "2330" if m == "TSE" else "8299"), NOW)
    def fetch(symbol):
        return {"symbol": symbol, "market": "TSE" if symbol == "2330" else "OTC",
                "date": NOW.date().isoformat(),
                "lastTrade": {"price": 42.0, "time": NOW.isoformat()}}
    report = audit_individual(raw, fetch=fetch, checked=NOW, sleep=lambda _: None)
    assert report["requests_made"] == 2
    assert report["fresh_executed"] == 2
    assert report["any_429"] is False


def test_missing_trade_time_not_promoted():
    _, raw = snapshot_audit(lambda m: payload(m, "2330" if m == "TSE" else "8299"), NOW)
    result = audit_individual(raw, fetch=lambda s: {
        "symbol": s, "market": "TSE" if s == "2330" else "OTC",
        "date": NOW.date().isoformat(), "lastTrade": {"price": 42.0},
        "closeTime": NOW.isoformat()
    }, checked=NOW, sleep=lambda _: None)
    assert result["fresh_executed"] == 0
    assert all(x["status"] == "NO_LAST_TRADE_EVIDENCE" for x in result["items"])


def test_429_is_classified_and_stops():
    _, raw = snapshot_audit(lambda m: payload(m, "2330" if m == "TSE" else "8299"), NOW)
    response = requests.Response()
    response.status_code = 429
    response.url = "https://api.fugle.tw/test"
    def fail(_):
        raise requests.HTTPError(response=response)
    result = audit_individual(raw, fetch=fail, checked=NOW, sleep=lambda _: None)
    assert error_category(requests.HTTPError(response=response)) == "RATE_LIMIT_429"
    assert result["any_429"] is True
    assert result["requests_made"] == 1


def test_twelve_symbol_limit_alternates_markets_and_stops_at_budget():
    tse = [{"symbol": str(2300 + i), "lastPrice": 35.0, "tradeVolume": 5000 - i}
           for i in range(7)]
    otc = [{"symbol": str(8100 + i), "lastPrice": 45.0, "tradeVolume": 5000 - i}
           for i in range(7)]
    raw = {"TSE": {"data": tse}, "OTC": {"data": otc}}
    selected = choose_samples(raw)
    assert len(selected) == 12
    assert [m for m, _ in selected] == ["TSE", "OTC"] * 6

    calls = []
    def fetch(symbol):
        calls.append(symbol)
        return {"symbol": symbol, "market": "TSE" if symbol.startswith("23") else "OTC",
                "date": NOW.date().isoformat(),
                "lastTrade": {"price": 40.0, "time": NOW.isoformat()}}
    report = audit_individual(raw, fetch=fetch, checked=NOW, sleep=lambda _: None)
    assert report["requested_limit"] == 12
    assert report["requests_made"] == 12
    assert report["fresh_executed"] == 12
    assert len(calls) == 12
    assert report["any_429"] is False
