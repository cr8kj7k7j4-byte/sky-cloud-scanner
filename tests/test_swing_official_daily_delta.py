import pytest

from research.collect_swing_official_daily_delta import roc_day, parse_market, join_pit


def test_roc_day():
    assert roc_day("1151103") == "2026-11-03"
    assert roc_day("115/11/03") == "2026-11-03"


def test_twse_and_tpex_daily_market_schema():
    twse = [{
        "Code":"2330","Date":"1151103",
        "OpeningPrice":"1,200", "HighestPrice":"1,210",
        "LowestPrice":"1,190","ClosingPrice":"1,205",
        "TradeVolume":"1,000,000", "TradeValue":"1200000000",
    } for _ in range(500)]
    tpex = [{
        "SecuritiesCompanyCode":"8086","Date":"1151103",
        "Open":"50","High":"52","Low":"49","Close":"51",
        "TradingShares":"600,000","TransactionAmount":"30600000",
    } for _ in range(400)]
    x, _ = parse_market(twse,"TWSE","2026-11-03")
    y, _ = parse_market(tpex,"TPEx","2026-11-03")
    assert x[0]["volume"] == 1000000.0
    assert y[0]["exchange"] == "TPEx"


def test_wrong_date_never_accepted():
    data=[{"Code":"2330","Date":"1151030",
            "OpeningPrice":"1200","HighestPrice":"1210",
            "LowestPrice":"1190","ClosingPrice":"1205",
            "TradeVolume":"1000"} for _ in range(500)]
    with pytest.raises(ValueError):
        parse_market(data,"TWSE","2026-11-03")


def test_pit_membership_must_match_actual_day_and_exchange():
    rows=[{"symbol":"2330","exchange":"TWSE","date":"2026-11-03","close":1205},
          {"symbol":"8086","exchange":"TPEx","date":"2026-11-03","close":51}]
    intervals=[{"symbol":"2330","exchange":"TWSE","listed_from":"2023-01-01","listed_to":None},
               {"symbol":"8086","exchange":"TPEx","listed_from":"2023-01-01","listed_to":"2026-10-31"}]
    kept, quarantined=join_pit(rows,intervals)
    assert [x["symbol"] for x in kept] == ["2330"]
    assert quarantined[0]["symbol"] == "8086"
