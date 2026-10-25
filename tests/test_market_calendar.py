from datetime import datetime
from zoneinfo import ZoneInfo
from src.market_calendar import build_session, validate_calendar, is_market_open

TZ=ZoneInfo("Asia/Taipei")

def test_calendar_contract_and_open_state():
    s=build_session("2026-10-22",is_trading_day=True,source="TWSE",source_as_of="2026-10-22T00:00:00+08:00")
    assert validate_calendar([s])["valid"] is True
    assert is_market_open(datetime(2026,10,22,10,0,tzinfo=TZ),[s]) is True

def test_holiday_is_closed():
    s=build_session("2026-10-23",is_trading_day=False,source="TWSE",source_as_of="2026-10-23T00:00:00+08:00")
    assert is_market_open(datetime(2026,10,23,10,0,tzinfo=TZ),[s]) is False
