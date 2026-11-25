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


def test_calendar_provider_failure_never_releases_paid_scan(monkeypatch):
    from src import trading_calendar
    def unavailable(*_args, **_kwargs):
        raise TimeoutError("official calendar timeout")
    monkeypatch.setattr(trading_calendar, "fetch_calendar", unavailable)
    for day in (date(2026, 11, 26), date(2026, 11, 28)):
        result = trading_calendar.check_trading_day(day)
        assert result["date"] == day.isoformat()
        assert result["market_open"] is False
        assert result["should_scan"] is False
        assert result["fail_open"] is False
        assert result["source_status"] == "HOLD"
        assert result["status"] == "HOLD_OFFICIAL_CALENDAR_UNAVAILABLE"
        assert "TimeoutError" in result["error"]


def test_calendar_verified_open_or_closed_still_obeys_official_evidence(monkeypatch):
    from src import trading_calendar
    monkeypatch.setattr(trading_calendar, "fetch_calendar", lambda: [
        {"Name": "農曆春節後開始交易日", "Date": "1150223",
         "Description": "農曆春節後開始交易。"},
        {"Name": "紀念日補假", "Date": "1151026", "Description": "補假。"},
    ])
    open_day = trading_calendar.check_trading_day(date(2026, 2, 23))
    closed_day = trading_calendar.check_trading_day(date(2026, 10, 26))
    assert open_day["should_scan"] is True
    assert open_day["source_status"] == "PASS"
    assert closed_day["should_scan"] is False
    assert closed_day["source_status"] == "PASS"


def test_official_calendar_empty_success_payload_blocks_paid_scan(monkeypatch):
    from src import trading_calendar
    class FakeResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return []
    monkeypatch.setattr(trading_calendar.requests, "get",
                        lambda *_args, **_kwargs: FakeResponse())
    result = trading_calendar.check_trading_day(date(2026, 11, 26))
    assert result["should_scan"] is False
    assert result["market_open"] is False
    assert result["fail_open"] is False
    assert result["source_status"] == "HOLD"
    assert result["status"] == "HOLD_OFFICIAL_CALENDAR_UNAVAILABLE"
    assert "TWSE_HOLIDAY_EMPTY_OR_INVALID_PAYLOAD" in result["error"]


def test_official_calendar_invalid_rows_block_paid_scan(monkeypatch):
    from src import trading_calendar
    class FakeResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return [None, 123, "invalid", {"Name": "not a dated holiday"}]
    monkeypatch.setattr(trading_calendar.requests, "get",
                        lambda *_args, **_kwargs: FakeResponse())
    result = trading_calendar.check_trading_day(date(2026, 11, 26))
    assert result["should_scan"] is False
    assert result["source_status"] == "HOLD"
    assert "TWSE_HOLIDAY_EMPTY_OR_INVALID_PAYLOAD" in result["error"]


def test_stale_official_calendar_year_never_certifies_target_day(monkeypatch):
    from src import trading_calendar
    monkeypatch.setattr(trading_calendar, "fetch_calendar", lambda: [
        {"Date": "1141026", "Name": "prior year closure", "Description": "補假。"}
    ])
    got = trading_calendar.check_trading_day(date(2026, 11, 26))
    assert got["source_status"] == "HOLD"
    assert got["status"] == "HOLD_OFFICIAL_CALENDAR_UNAVAILABLE"
    assert got["should_scan"] is False
    assert got["fail_open"] is False
    assert "TWSE_HOLIDAY_TARGET_YEAR_NOT_VERIFIED" in got["error"]


def test_invalid_roc_calendar_date_cannot_verify_trading_year(monkeypatch):
    from src import trading_calendar
    assert _roc_to_iso("1150231") is None
    assert _roc_to_iso("1151330") is None
    monkeypatch.setattr(trading_calendar, "fetch_calendar", lambda: [
        {"Date": "1150231", "Name": "impossible day"}
    ])
    got = trading_calendar.check_trading_day(date(2026, 11, 26))
    assert got["should_scan"] is False
    assert got["source_status"] == "HOLD"
    assert "TWSE_HOLIDAY_TARGET_YEAR_NOT_VERIFIED" in got["error"]
