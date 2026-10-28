from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.swing_v11_live_scanner import signal_freshness
from src.swing_v11_market_observer import summarize


def test_v11_freshness_allows_recent_day():
    assert signal_freshness("2026-10-27", date(2026, 10, 28))["fresh"] is True


def test_v11_freshness_blocks_stale_historical_bundle():
    result = signal_freshness("2026-10-22", date(2026, 10, 28))
    assert result["fresh"] is False
    assert result["reason"] == "STALE_OR_FUTURE_SIGNAL_DATE"


def test_v11_freshness_blocks_future_or_invalid_date():
    assert not signal_freshness("2026-10-29", date(2026, 10, 28))["fresh"]
    assert not signal_freshness("not-a-date", date(2026, 10, 28))["fresh"]


def test_whole_market_observer_never_authorizes_trading():
    now = datetime(2026, 10, 28, 9, 15, tzinfo=ZoneInfo("Asia/Taipei"))
    universe = [{"symbol": "1111", "exchange": "TWSE"}]
    quotes = [{
        "symbol": "1111", "exchange": "TWSE",
        "change_pct": 1.25, "bid": 25, "ask": 25.05,
    }]
    result = summarize(universe, quotes, {"twse": 1, "tpex": 0}, [], now)
    assert result["quote_count"] == 1
    assert result["strategy_signal"] is False
    assert result["trading_authorized"] is False
    assert result["strict_tpex_realtime_certified"] is False
    assert result["operational_coverage_healthy"] is False
