from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.quote_provider import collect_market_quotes

NOW = datetime(2026, 11, 6, 10, 15, tzinfo=ZoneInfo("Asia/Taipei"))
UNIVERSE = [
    {"symbol": "1001", "exchange": "TWSE"},
    {"symbol": "2001", "exchange": "TPEx"},
]


def fugle_row(symbol, age=10):
    return {"symbol": symbol, "quote_source": "Fugle bulk snapshot",
            "last": 50, "quote_date": NOW.date().isoformat(),
            "last_trade_timestamp": int((NOW - timedelta(seconds=age)).timestamp() * 1_000_000)}


def mis_row(symbol):
    return {"symbol": symbol, "quote_source": "TWSE MIS",
            "last": 50, "quote_date": NOW.strftime("%Y%m%d"),
            "quote_time": (NOW - timedelta(seconds=10)).strftime("%H:%M:%S")}


def test_primary_fugle_is_selected_without_calling_mis():
    def forbidden(_):
        raise AssertionError("MIS must not be called when Fugle primary passes")
    result = collect_market_quotes(
        UNIVERSE, now=NOW,
        fugle_fetch=lambda _, trading_date: ([fugle_row("1001"), fugle_row("2001")], []),
        mis_fetch=forbidden,
    )
    assert result["provider"] == "Fugle bulk snapshot"
    assert not result["fallback_used"]
    assert result["audit"]["valid_whole_market_operational"]
    assert not result["official_tpex_realtime_certified"]
    assert result["primary_evidence"]["valid_quote_count"] == 2


def test_missing_fugle_trade_time_falls_back_without_mixing():
    result = collect_market_quotes(
        UNIVERSE, now=NOW,
        fugle_fetch=lambda _, trading_date: ([
            {"symbol": "1001", "quote_source": "Fugle bulk snapshot",
             "last": 50, "quote_date": NOW.date().isoformat()}], []),
        mis_fetch=lambda _: ([mis_row("1001"), mis_row("2001")], []),
    )
    assert result["fallback_used"]
    assert result["primary_status"] == "BLOCKED_EXTERNAL_DATA"
    assert result["primary_evidence"]["valid_quote_count"] == 0
    assert len(result["rows"]) == 2
    assert all(x["quote_source"] == "TWSE MIS" for x in result["rows"])


def test_two_partial_sources_do_not_create_false_full_market_pass():
    result = collect_market_quotes(
        UNIVERSE, now=NOW,
        fugle_fetch=lambda _, trading_date: ([fugle_row("1001")], []),
        mis_fetch=lambda _: ([mis_row("2001")], []),
    )
    assert result["audit"]["valid_whole_market_operational"] is False
    assert result["audit"]["valid_quote_count"] == 1


def test_stale_fugle_and_failed_mis_fail_closed():
    result = collect_market_quotes(
        UNIVERSE, now=NOW,
        fugle_fetch=lambda _, trading_date: ([fugle_row("1001", age=3600)], []),
        mis_fetch=lambda _: (_ for _ in ()).throw(PermissionError("denied")),
    )
    assert result["audit"]["valid_quote_count"] == 0
    assert not result["audit"]["valid_whole_market_operational"]


def test_w3a_primary_audit_reports_exchange_specific_rejection():
    result = collect_market_quotes(
        UNIVERSE, now=NOW,
        fugle_fetch=lambda _, trading_date: (
            [fugle_row("1001"), dict(fugle_row("2001"), last_trade_timestamp=None)], []
        ),
        mis_fetch=lambda _: ([], ["MIS_EMPTY"]),
    )
    assert result["fallback_used"] is True
    assert result["primary_evidence"]["received_by_exchange"] == {"TWSE": 1, "TPEx": 1}
    assert result["primary_evidence"]["rejected_by_exchange"]["TPEx"] == {
        "STALE_OR_UNVERIFIED_EXECUTED_TRADE": 1
    }
    assert result["audit"]["valid_quote_count"] == 0
    assert result["audit"]["status"] == "BLOCKED_EXTERNAL_DATA"


def test_w3a_primary_complete_source_does_not_get_mixed_with_mis():
    def must_not_call_mis(_):
        raise AssertionError("no MIS call after valid Fugle cross-market coverage")
    result = collect_market_quotes(
        UNIVERSE, now=NOW,
        fugle_fetch=lambda _, trading_date: (
            [fugle_row("1001"), fugle_row("2001")], []
        ),
        mis_fetch=must_not_call_mis,
    )
    assert result["fallback_used"] is False
    assert {row["symbol"] for row in result["rows"]} == {"1001", "2001"}
    assert all(row["quote_source"] == "Fugle bulk snapshot" for row in result["rows"])
    assert result["primary_evidence"]["received_by_exchange"] == {"TWSE": 1, "TPEx": 1}
    assert result["primary_evidence"]["missing_by_exchange"] == {"TWSE": 0, "TPEx": 0}
