from datetime import datetime
from zoneinfo import ZoneInfo

from src.swing_split_scope_scanner import parse_daily_rows, evaluate_daily_scope

TZ=ZoneInfo("Asia/Taipei")


def test_official_daily_twse_and_tpex_parse():
    a=parse_daily_rows([
       {"Date":"1151103","Code":"2330","ClosingPrice":"980","TradeVolume":"10,000",
        "TradeValue":"9,800,000","Change":"+5"},
       {"Date":"1151103","Code":"1234","ClosingPrice":"-","TradeVolume":"0",
        "TradeValue":"0","Change":"-"},
    ],"TWSE")
    b=parse_daily_rows([
       {"Date":"1151103","SecuritiesCompanyCode":"6488","Close":"85",
        "TradingShares":"100,000","TransactionAmount":"8,500,000","Change":"-1"}
    ],"TPEx")
    assert a["2330"]["date"]=="2026-11-03"
    assert a["2330"]["volume_lots"]==10
    assert b["6488"]["change_pct"]<0
    assert "1234" not in a


def test_daily_full_market_is_not_live_market():
    universe=[{"symbol":"2330","exchange":"TWSE"},{"symbol":"6488","exchange":"TPEx"}]
    twse={"2330":{"date":"2026-11-03","symbol":"2330"}}
    tpex={"6488":{"date":"2026-11-03","symbol":"6488"}}
    out=evaluate_daily_scope(universe,twse,tpex,datetime(2026,11,4,9,30,tzinfo=TZ))
    assert out["daily_cross_section_coverage_pct"]==100
    assert out["daily_scope_qualified"] is True
    assert out["signal_date"]=="2026-11-03"


def test_mismatched_day_blocks():
    universe=[{"symbol":"2330","exchange":"TWSE"},{"symbol":"6488","exchange":"TPEx"}]
    twse={"2330":{"date":"2026-11-03","symbol":"2330"}}
    tpex={"6488":{"date":"2026-11-02","symbol":"6488"}}
    out=evaluate_daily_scope(universe,twse,tpex,datetime(2026,11,4,9,30,tzinfo=TZ))
    assert out["daily_scope_qualified"] is False


def test_same_day_unclosed_snapshot_blocks():
    universe=[{"symbol":"2330","exchange":"TWSE"}]
    rows={"2330":{"date":"2026-11-04","symbol":"2330"}}
    out=evaluate_daily_scope(universe,rows,{},datetime(2026,11,4,9,30,tzinfo=TZ))
    assert not out["daily_scope_qualified"]
