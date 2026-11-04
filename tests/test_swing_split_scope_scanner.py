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


def test_same_day_quote_requires_fresh_timestamp():
    from src.swing_split_scope_scanner import quote_time_freshness
    now=datetime(2026,11,4,9,35,tzinfo=TZ)
    microseconds=int(now.timestamp()*1_000_000)
    stamp,status=quote_time_freshness({"lastUpdated":microseconds},now)
    assert status=="FRESH" and stamp.startswith("2026-11-04")
    assert quote_time_freshness({"lastUpdated":microseconds-20*60*1_000_000},now)[1]=="STALE_OR_FUTURE_TIMESTAMP"
    assert quote_time_freshness({},now)[1]=="MISSING_OR_INVALID_TIMESTAMP"


def test_closeprice_only_cannot_be_promoted_to_live_lastprice(monkeypatch, tmp_path):
    from datetime import timedelta
    from src import swing_split_scope_scanner as scanner

    now=datetime.now(TZ)
    previous=(now.date()-timedelta(days=1)).strftime("%Y%m%d")
    # The daily-source date is prior day, and the candidate's closePrice is
    # present; a missing lastPrice must still fail the live-price test.
    monkeypatch.setattr(scanner, "OUT", tmp_path)
    monkeypatch.setattr(scanner, "load_official_universe", lambda: (
        [{"symbol":"2330","exchange":"TWSE"},
         {"symbol":"6488","exchange":"TPEx"}],
        {"twse":1,"tpex":1,"warnings":[]},
    ))
    def fake_daily(url, **_):
        if url == scanner.TWSE_DAILY:
            return [{"Code":"2330","Date":previous,"ClosingPrice":"50",
                     "TradeVolume":"1000000","TradeValue":"50000000","Change":"1"}]
        return [{"SecuritiesCompanyCode":"6488","Date":previous,"Close":"60",
                 "TradingShares":"1000000","TransactionAmount":"60000000","Change":"2"}]
    monkeypatch.setattr(scanner, "get_json", fake_daily)
    monkeypatch.setattr(scanner, "get_quote", lambda _symbol: {
        "date":now.date().isoformat(), "lastPrice":None, "closePrice":62,
        "lastUpdated":int(now.timestamp()*1000),
    })

    report=scanner.run(deep_n=2)
    assert report["daily_scope_status"] == "PASS_DAILY_CROSS_SECTION"
    assert report["live_quote_requested"] == 2
    assert report["live_quote_available"] == 0
    assert report["live_quote_timestamp_verified"] == 0
    assert all(x["current_price"] is None for x in report["candidates"])
    assert report["live_whole_market_certified"] is False


def test_tpex_backup_source_is_distinct_in_daily_evidence():
    rows=parse_daily_rows([
        {"Date":"1151104","SecuritiesCompanyCode":"6488","Close":"85",
         "TradingShares":"100,000","TransactionAmount":"8,500,000","Change":"-1"}
    ], "TPEx", source_label="TPEx mainboard_quotes")
    assert rows["6488"]["source"]=="TPEx mainboard_quotes"


def test_primary_tpex_date_mismatch_uses_only_date_matching_official_backup(monkeypatch, tmp_path):
    from datetime import timedelta
    from src import swing_split_scope_scanner as scanner
    now=datetime.now(TZ)
    wanted=(now.date()-timedelta(days=1)).strftime("%Y%m%d")
    stale=(now.date()-timedelta(days=2)).strftime("%Y%m%d")
    monkeypatch.setattr(scanner, "OUT", tmp_path)
    monkeypatch.setattr(scanner, "load_official_universe", lambda: (
        [{"symbol":"2330","exchange":"TWSE"},
         {"symbol":"6488","exchange":"TPEx"}],
        {"twse":1,"tpex":1,"warnings":[]},
    ))
    seen=[]
    def fake_get_json(url, **_):
        seen.append(url)
        if url==scanner.TWSE_DAILY:
            return [{"Code":"2330","Date":wanted,"ClosingPrice":"50",
                     "TradeVolume":"1000000","TradeValue":"50000000","Change":"1"}]
        if url==scanner.TPEX_DAILY:
            return [{"SecuritiesCompanyCode":"6488","Date":stale,"Close":"60",
                     "TradingShares":"1000000","TransactionAmount":"60000000","Change":"2"}]
        if url==scanner.TPEX_BACKUP:
            return [{"SecuritiesCompanyCode":"6488","Date":wanted,"Close":"60",
                     "TradingShares":"1000000","TransactionAmount":"60000000","Change":"2"}]
        raise AssertionError(url)
    monkeypatch.setattr(scanner, "get_json", fake_get_json)
    monkeypatch.setattr(scanner, "get_quote", lambda _: {})
    report=scanner.run(deep_n=1)
    assert scanner.TPEX_BACKUP in seen
    assert report["daily_scope_status"]=="PASS_DAILY_CROSS_SECTION"
    assert report["official_tpex_source_used"]=="mainboard_quotes"
    assert report["live_whole_market_certified"] is False
    assert report["live_quote_available"]==0
