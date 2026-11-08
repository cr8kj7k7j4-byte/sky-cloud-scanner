"""W3A fail-closed quote coverage diagnostics (offline fixtures only)."""
from datetime import datetime
from zoneinfo import ZoneInfo

from src.realtime_quote_evidence import validate_whole_market_rows, fugle_executed_trade, mis_executed_trade_row

NOW = datetime(2026, 11, 6, 10, 15, tzinfo=ZoneInfo("Asia/Taipei"))
POOL = [
    {"symbol": "2330", "exchange": "TWSE"},
    {"symbol": "8088", "exchange": "TPEx"},
]


def _fugle(symbol, **extra):
    return {
        "symbol": symbol,
        "last": 50.0,
        "quote_source": "Fugle bulk snapshot",
        "quote_date": NOW.date().isoformat(),
        "last_trade_timestamp": NOW.isoformat(),
        **extra,
    }


def test_missing_exchange_data_does_not_look_like_no_trade_setup():
    result = validate_whole_market_rows(POOL, [_fugle("2330")], now=NOW)
    assert result["status"] == "BLOCKED_EXTERNAL_DATA"
    assert result["missing_by_exchange"] == {"TWSE": 0, "TPEx": 1}
    assert result["by_exchange"]["TPEx"]["valid"] == 0


def test_invalid_rows_are_received_but_not_counted_as_missing():
    result = validate_whole_market_rows(
        POOL, [_fugle("2330"), _fugle("8088", last_trade_timestamp=None)],
        now=NOW,
    )
    assert result["missing_by_exchange"] == {"TWSE": 0, "TPEx": 0}
    assert result["rejected"]["STALE_OR_UNVERIFIED_EXECUTED_TRADE"] == 1
    assert result["valid_quote_count"] == 1


def test_trial_and_infinite_bulk_quotes_cannot_certify_market():
    for bad in (_fugle("8088", isTrial=True), _fugle("8088", last=float("inf"))):
        result = validate_whole_market_rows(
            POOL, [_fugle("2330"), bad],
            now=NOW, min_coverage_pct=100, min_exchange_pct=100,
        )
        assert result["valid_whole_market_operational"] is False
        assert result["valid_quote_count"] == 1


def test_individual_quotes_reject_nonfinite_prices():
    quote = {
        "date": NOW.date().isoformat(),
        "lastTrade": {"price": float("inf"), "time": NOW.isoformat()},
    }
    assert fugle_executed_trade(quote, NOW)[2] == "MISSING_EXECUTED_LAST_PRICE"
    assert mis_executed_trade_row(
        {"last": float("inf"), "quote_date": "20261106", "quote_time": "10:14:30"},
        NOW,
    ) is False


def test_fresh_valid_cross_exchange_rows_preserved():
    result = validate_whole_market_rows(
        POOL, [_fugle("2330"), _fugle("8088")],
        now=NOW, min_coverage_pct=100, min_exchange_pct=100,
    )
    assert result["status"] == "PASS_VALID_EXECUTED_LIVE"
    assert result["missing_by_exchange"] == {"TWSE": 0, "TPEx": 0}
