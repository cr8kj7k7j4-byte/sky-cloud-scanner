from datetime import date

from src.trading_calendar import classify_date, _roc_to_iso


def test_roc_date_conversion():
    assert _roc_to_iso("1151026")=="2026-10-26"


def test_official_holiday_closes_market():
    rows=[{
        "Name":"臺灣光復暨金門古寧頭大捷紀念日",
        "Date":"1151026",
        "Weekday":"一",
        "Description":"於10月26日（星期一）補假。",
    }]
    out=classify_date(date(2026,10,26),rows)
    assert out["market_open"] is False
    assert out["status"]=="CLOSED_OFFICIAL_SCHEDULE"


def test_explicit_start_trading_day_is_open():
    rows=[{
        "Name":"農曆春節後開始交易日",
        "Date":"1150223",
        "Weekday":"一",
        "Description":"農曆春節後開始交易。",
    }]
    out=classify_date(date(2026,2,23),rows)
    assert out["market_open"] is True
    assert out["status"]=="OPEN_EXPLICIT"


def test_regular_weekday_defaults_open():
    out=classify_date(date(2026,10,27),[])
    assert out["market_open"] is True
    assert out["status"]=="OPEN_REGULAR_WEEKDAY"


def test_weekend_defaults_closed():
    out=classify_date(date(2026,10,24),[])
    assert out["market_open"] is False
    assert out["status"]=="CLOSED_WEEKEND"
