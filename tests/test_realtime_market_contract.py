from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.realtime_quote_evidence import (
    fugle_executed_trade,
    market_scope,
    mis_executed_trade_row,
)
from src.sky_command_router import route_command

TPE = ZoneInfo("Asia/Taipei")
NOW = datetime(2026, 11, 4, 10, 15, tzinfo=TPE)


def test_fugle_confirmed_last_trade_price_and_timestamp():
    q = {
        "date": "2026-11-04", "closePrice": 77.5,
        "lastTrade": {"price": 77.3, "time": int(NOW.timestamp() * 1_000_000)},
    }
    price, dt, status = fugle_executed_trade(q, NOW)
    assert status == "FRESH_EXECUTED_TRADE"
    assert price == 77.3 and dt.date() == NOW.date()



def test_fugle_iso8601_executed_trade_time_is_parsed_with_timezone():
    q = {
        "date": NOW.date().isoformat(),
        "lastTrade": {"price": 62.5, "time": NOW.isoformat()},
    }
    price, stamp, state = fugle_executed_trade(q, NOW)
    assert state == "FRESH_EXECUTED_TRADE"
    assert price == 62.5
    assert stamp == NOW
    q["lastTrade"]["time"] = NOW.strftime("%Y-%m-%dT%H:%M:%S")
    assert fugle_executed_trade(q, NOW)[2] == "MISSING_EXECUTED_TRADE_TIME"
    q["lastTrade"]["time"] = (NOW - timedelta(minutes=5)).isoformat()
    assert fugle_executed_trade(q, NOW)[2] == "STALE_EXECUTED_TRADE"


def test_fugle_iso_snapshot_timestamp_does_not_substitute_trade_time():
    q = {
        "date": NOW.date().isoformat(), "lastPrice": 62.5,
        "lastUpdated": NOW.isoformat(), "closePrice": 62.5
    }
    assert fugle_executed_trade(q, NOW)[2] == "MISSING_EXECUTED_TRADE_TIME"


def test_fugle_iso_bulk_rows_require_real_execution_time():
    from src.realtime_quote_evidence import validate_whole_market_rows
    pool = [
        {"symbol": "2330", "exchange": "TWSE"},
        {"symbol": "8088", "exchange": "TPEx"},
    ]
    good = [
        {"symbol": "2330", "last": 60, "quote_source": "Fugle bulk snapshot",
         "last_trade_timestamp": NOW.isoformat(), "quote_date": NOW.date().isoformat()},
        {"symbol": "8088", "last": 50, "quote_source": "Fugle bulk snapshot",
         "last_trade_timestamp": NOW.isoformat(), "quote_date": NOW.date().isoformat()},
    ]
    result = validate_whole_market_rows(pool, good, now=NOW, min_coverage_pct=100, min_exchange_pct=100)
    assert result["valid_whole_market_operational"] is True
    assert result["valid_quote_count"] == 2
    good[0]["last_trade_timestamp"] = None
    result = validate_whole_market_rows(pool, good, now=NOW, min_coverage_pct=100, min_exchange_pct=100)
    assert result["valid_whole_market_operational"] is False
    assert result["valid_quote_count"] == 1


def test_reference_and_close_only_never_count_as_executed_live():
    for q in (
        {"date": "2026-11-04", "closePrice": 77.5,
         "closeTime": int(NOW.timestamp() * 1_000_000)},
        {"date": "2026-11-04", "referencePrice": 77.5,
         "lastTrade": {"time": int(NOW.timestamp() * 1_000_000)}},
    ):
        p, _, status = fugle_executed_trade(q, NOW)
        assert p is None and status == "MISSING_EXECUTED_LAST_PRICE"


def test_lastupdated_without_trade_time_is_not_a_trade():
    q = {"date": "2026-11-04", "lastPrice": 78.2,
         "lastUpdated": int(NOW.timestamp() * 1_000_000)}
    p, _, status = fugle_executed_trade(q, NOW)
    assert p is None and status == "MISSING_EXECUTED_TRADE_TIME"


def test_fugle_stale_date_future_and_stale_time_rejected():
    q = {"date": "2026-11-03", "lastPrice": 80,
         "closeTime": int(NOW.timestamp() * 1_000_000)}
    assert fugle_executed_trade(q, NOW)[2] == "STALE_TRADING_DATE"
    q["date"] = "2026-11-04"
    q["closeTime"] = int((NOW - timedelta(minutes=6)).timestamp() * 1_000_000)
    assert fugle_executed_trade(q, NOW)[2] == "STALE_EXECUTED_TRADE"
    q["closeTime"] = int((NOW + timedelta(minutes=3)).timestamp() * 1_000_000)
    assert fugle_executed_trade(q, NOW)[2] == "FUTURE_TRADE_TIMESTAMP"


def test_mis_quote_requires_exchange_day_and_fresh_last_trade():
    q = {"quote_date": "20261104", "quote_time": "10:14:40", "last": 40.5}
    assert mis_executed_trade_row(q, NOW) is True
    q["quote_date"] = None
    assert mis_executed_trade_row(q, NOW) is False
    q["quote_date"] = "20261104"
    q["quote_time"] = "09:10:00"
    assert mis_executed_trade_row(q, NOW) is False
    q["quote_time"] = "10:14:40"
    q["last"] = None
    assert mis_executed_trade_row(q, NOW) is False


def test_market_scope_never_conflates_daily_or_candidate_with_live_universe():
    assert market_scope({
        "operational_full_market_scan": True,
        "quote_coverage_pct": 98.69,
        "daily_scope_status": "PASS_DAILY_CROSS_SECTION",
    }) == "OFFICIAL_DAILY_CROSS_SECTION"
    assert market_scope({
        "quote_scope": "FROZEN_SIGNAL_CANDIDATES_ONLY",
        "quote_coverage_pct": 100,
        "operational_full_market_scan": True,
    }) == "CANDIDATES_ONLY_REALTIME"
    assert market_scope({
        "quote_scope": "WHOLE_MARKET_EXECUTED_LIVE",
        "live_whole_market_certified": True,
    }) == "WHOLE_MARKET_REALTIME_OPERATIONAL"


def test_missing_sky_realtime_routes_are_explicit():
    for name in ("Sky 全市場即時行情", "Sky 當沖空方研究 掃一下",
                 "Sky 持倉監控", "Sky v1.4 Dynamic Capital Rotation 掃一下"):
        route = route_command(name)
        assert route.realtime_required is True
        assert route.command_family != "SKY_UNRECOGNIZED"
    assert route_command("Sky 當沖空方研究 掃一下").data_mode.endswith("_BLOCKED")
    assert route_command("Sky 回測目前模型").data_mode == "HISTORICAL_PIT"


def test_v11_candidate_without_executed_trade_never_enters_overlay(monkeypatch):
    from src import swing_v11_live_scanner as v11
    from src import realtime_quote_evidence as qev

    target = {"symbol": "1234", "exchange": "TWSE", "name": "x"}
    signal = {"symbol": "1234"}
    monkeypatch.setattr(v11, "fetch_mis_quotes", lambda *a, **kw: ([], []))
    monkeypatch.setattr(v11, "get_quote", lambda symbol: {
        "date": NOW.date().isoformat(),
        "closePrice": 42, "lastUpdated": int(NOW.timestamp() * 1_000_000),
        "openPrice": 40,
    })
    quotes, warnings, meta = v11.fetch_candidate_live_quotes([signal], [target], now=NOW)
    assert quotes == {}
    assert meta["missing"] == 1
    assert any("MISSING_EXECUTED_LAST_PRICE" in x for x in warnings)


def test_v11_candidate_with_fresh_executed_trade_can_be_observed(monkeypatch):
    from src import swing_v11_live_scanner as v11
    target = {"symbol": "1234", "exchange": "TWSE", "name": "x"}
    monkeypatch.setattr(v11, "fetch_mis_quotes", lambda *a, **kw: ([], []))
    monkeypatch.setattr(v11, "get_quote", lambda symbol: {
        "date": NOW.date().isoformat(), "lastTrade": {
            "price": 40.2, "time": int(NOW.timestamp() * 1_000_000)
        }, "openPrice": 40, "previousClose": 39,
    })
    quotes, warnings, meta = v11.fetch_candidate_live_quotes(
        [{"symbol": "1234"}], [target], now=NOW
    )
    assert quotes["1234"]["last"] == 40.2
    assert meta["fugle"] == 1
    assert meta["requested"] == 1


# W3A data-integrity regressions: exercised by the existing realtime-contract CI.
def test_w3a_missing_otc_quotes_are_reported_separately():
    from src.realtime_quote_evidence import validate_whole_market_rows
    pool = [{"symbol": "2330", "exchange": "TWSE"}, {"symbol": "8088", "exchange": "TPEx"}]
    rows = [{"symbol": "2330", "last": 50, "quote_source": "Fugle bulk snapshot",
             "quote_date": NOW.date().isoformat(), "last_trade_timestamp": NOW.isoformat()}]
    result = validate_whole_market_rows(pool, rows, now=NOW)
    assert result["missing_by_exchange"] == {"TWSE": 0, "TPEx": 1}
    assert result["status"] == "BLOCKED_EXTERNAL_DATA"


def test_w3a_invalid_otc_timestamp_is_received_but_rejected():
    from src.realtime_quote_evidence import validate_whole_market_rows
    pool = [{"symbol": "2330", "exchange": "TWSE"}, {"symbol": "8088", "exchange": "TPEx"}]
    rows = [{"symbol": "2330", "last": 50, "quote_source": "Fugle bulk snapshot",
             "quote_date": NOW.date().isoformat(), "last_trade_timestamp": NOW.isoformat()},
            {"symbol": "8088", "last": 51, "quote_source": "Fugle bulk snapshot",
             "quote_date": NOW.date().isoformat(), "last_trade_timestamp": None}]
    result = validate_whole_market_rows(pool, rows, now=NOW)
    assert result["missing_by_exchange"] == {"TWSE": 0, "TPEx": 0}
    assert result["valid_quote_count"] == 1


def test_w3a_trial_and_infinite_values_fail_closed():
    from src.realtime_quote_evidence import validate_whole_market_rows
    pool = [{"symbol": "2330", "exchange": "TWSE"}, {"symbol": "8088", "exchange": "TPEx"}]
    base = {"quote_source": "Fugle bulk snapshot",
            "quote_date": NOW.date().isoformat(), "last_trade_timestamp": NOW.isoformat()}
    for override in ({"last": float("inf")}, {"last": 50, "isTrial": True}):
        rows = [dict(base, symbol="2330", last=50), dict(base, symbol="8088", **override)]
        result = validate_whole_market_rows(pool, rows, now=NOW,
                                            min_coverage_pct=100, min_exchange_pct=100)
        assert result["valid_quote_count"] == 1
        assert result["valid_whole_market_operational"] is False


def test_w3a_market_data_reason_breakdown_is_exchange_specific():
    from src.realtime_quote_evidence import validate_whole_market_rows
    pool = [
        {"symbol": "2330", "exchange": "TWSE"},
        {"symbol": "1101", "exchange": "TWSE"},
        {"symbol": "8088", "exchange": "TPEx"},
    ]
    base = {"quote_source": "Fugle bulk snapshot",
            "quote_date": NOW.date().isoformat(), "last_trade_timestamp": NOW.isoformat()}
    rows = [
        dict(base, symbol="2330", last=45),
        dict(base, symbol="1101", last=50, isTrial=True),
        dict(base, symbol="8088", last=50, last_trade_timestamp=None),
    ]
    result = validate_whole_market_rows(pool, rows, now=NOW)
    assert result["received_by_exchange"] == {"TWSE": 2, "TPEx": 1}
    assert result["missing_by_exchange"] == {"TWSE": 0, "TPEx": 0}
    assert result["rejected_by_exchange"]["TWSE"] == {"TRIAL_QUOTE": 1}
    assert result["rejected_by_exchange"]["TPEx"] == {"STALE_OR_UNVERIFIED_EXECUTED_TRADE": 1}
    assert result["rejected"] == {
        "TRIAL_QUOTE": 1,
        "STALE_OR_UNVERIFIED_EXECUTED_TRADE": 1,
    }
    assert result["valid_whole_market_operational"] is False


def test_w3a_integrated_fugle_first_route_keeps_provider_evidence():
    from src.quote_provider import collect_market_quotes
    pool = [{"symbol": "2330", "exchange": "TWSE"}, {"symbol": "8088", "exchange": "TPEx"}]
    rows = [
        {"symbol": code, "last": 60, "quote_date": NOW.date().isoformat(),
         "quote_source": "Fugle bulk snapshot", "last_trade_timestamp": NOW.isoformat()}
        for code in ("2330", "8088")
    ]
    result = collect_market_quotes(
        pool, now=NOW,
        fugle_fetch=lambda universe, trading_date: (rows, []),
        mis_fetch=lambda _: (_ for _ in ()).throw(
            AssertionError("MIS must not be queried when paid primary passes")
        ),
    )
    assert result["provider"] == "Fugle bulk snapshot"
    assert result["fallback_used"] is False
    assert result["primary_evidence"]["valid_quote_count"] == 2
    assert result["primary_evidence"]["missing_by_exchange"] == {"TWSE": 0, "TPEx": 0}


def test_w3a_integrated_route_never_mixes_two_partial_sources():
    from src.quote_provider import collect_market_quotes
    pool = [{"symbol": "2330", "exchange": "TWSE"}, {"symbol": "8088", "exchange": "TPEx"}]
    a = {"symbol": "2330", "last": 60, "quote_date": NOW.date().isoformat(),
         "quote_source": "Fugle bulk snapshot", "last_trade_timestamp": NOW.isoformat()}
    b = {"symbol": "8088", "last": 60, "quote_date": NOW.strftime("%Y%m%d"),
         "quote_time": "10:14:30", "quote_source": "TWSE MIS"}
    result = collect_market_quotes(
        pool, now=NOW,
        fugle_fetch=lambda universe, trading_date: ([a], []),
        mis_fetch=lambda universe: ([b], []),
    )
    assert result["fallback_used"] is True
    assert result["audit"]["valid_whole_market_operational"] is False
    assert result["audit"]["valid_quote_count"] == 1
    assert result["primary_evidence"]["valid_quote_count"] == 1
    assert result["primary_evidence"]["missing_by_exchange"]["TPEx"] == 1
    assert all(row["quote_source"] == "TWSE MIS" for row in result["rows"])
