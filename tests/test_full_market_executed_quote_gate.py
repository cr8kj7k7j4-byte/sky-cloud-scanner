from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.realtime_quote_evidence import validate_whole_market_rows

TPE = ZoneInfo("Asia/Taipei")
NOW = datetime(2026, 11, 4, 10, 15, 0, tzinfo=TPE)


def universe():
    return [
        {"symbol": "1001", "exchange": "TWSE"},
        {"symbol": "1002", "exchange": "TWSE"},
        {"symbol": "2001", "exchange": "TPEx"},
        {"symbol": "2002", "exchange": "TPEx"},
    ]


def mis(symbol, age=15, date="20261104", price=40):
    moment = NOW - timedelta(seconds=age)
    return {
        "symbol": symbol, "quote_source": "TWSE MIS", "last": price,
        "quote_date": date, "quote_time": moment.strftime("%H:%M:%S"),
    }


def test_both_exchanges_covered_and_fresh():
    result = validate_whole_market_rows(
        universe(), [mis(x["symbol"]) for x in universe()], NOW,
        min_coverage_pct=80, min_exchange_pct=70,
    )
    assert result["valid_whole_market_operational"] is True
    assert result["valid_quote_count"] == 4
    assert result["by_exchange"]["TPEx"]["coverage_pct"] == 100.0
    assert result["otc_mis_is_official_tpex_live"] is False


def test_no_full_market_certification_from_tse_only():
    result = validate_whole_market_rows(
        universe(), [mis("1001"), mis("1002")], NOW,
        min_coverage_pct=50, min_exchange_pct=70,
    )
    assert result["valid_whole_market_operational"] is False
    assert result["by_exchange"]["TPEx"]["valid"] == 0


def test_missing_execution_or_date_is_not_valid_market_coverage():
    rows = [
        mis("1001", date="20261103"),
        mis("1002", age=3600),
        mis("2001", price=None),
        {"symbol": "2002", "quote_source": "TWSE MIS",
         "last": 50, "quote_time": "10:14:55"},
    ]
    result = validate_whole_market_rows(universe(), rows, NOW)
    assert result["status"] == "BLOCKED_EXTERNAL_DATA"
    assert result["valid_quote_count"] == 0
    assert result["quote_scope"] == "PARTIAL_EXECUTED_LIVE"


def test_bulk_snapshot_without_last_trade_clock_cannot_count_as_live():
    payload = {
        "symbol": "1001", "quote_source": "Fugle bulk snapshot",
        "last": 44, "quote_date": "2026-11-04",
        "quote_time": int(NOW.timestamp() * 1_000_000),
        # No last_trade_timestamp, only update/download time.
    }
    result = validate_whole_market_rows(universe(), [payload], NOW)
    assert result["valid_quote_count"] == 0


def test_bulk_snapshot_with_actual_trade_clock_is_eligible():
    payload = {
        "symbol": "1001", "quote_source": "Fugle bulk snapshot",
        "last": 44, "quote_date": "2026-11-04",
        "last_trade_timestamp": int(NOW.timestamp() * 1_000_000),
    }
    result = validate_whole_market_rows(universe(), [payload], NOW)
    assert result["valid_quote_count"] == 1


def test_a_stale_duplicate_never_overwrites_a_fresh_quote():
    results = validate_whole_market_rows(
        universe(), [mis("1001"), mis("1001", age=99999)], NOW,
    )
    assert results["valid_quote_count"] == 1
    assert results["accepted_rows"][0]["quote_time"] == "10:14:45"


def test_unknown_quote_source_is_not_eligible():
    q = mis("1001")
    q["quote_source"] = "UNATTRIBUTED_VENDOR"
    result = validate_whole_market_rows(universe(), [q], NOW)
    assert result["valid_quote_count"] == 0
    assert result["valid_whole_market_operational"] is False


def test_main_market_contract_uses_eighty_percent_minimum():
    from src.sky_unified_commands import operational_market_evidence_ok
    baseline = {
        "available": True, "operational_full_market_scan": True,
        "quote_scope": "WHOLE_MARKET_EXECUTED_LIVE",
        "live_whole_market_certified": True,
    }
    assert not operational_market_evidence_ok({**baseline, "quote_coverage_pct": 79.99})
    assert operational_market_evidence_ok({**baseline, "quote_coverage_pct": 80.0})
