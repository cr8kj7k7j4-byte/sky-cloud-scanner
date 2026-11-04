import pytest
from datetime import date

from research.backfill_swing_official_dated_history import _validated_market_table


def twse_table(date_str="20261030"):
    return {
        "stat":"OK","date":date_str,
        "tables":[{"fields":["證券代號","證券名稱","成交股數","成交筆數",
                             "成交金額","開盤價","最高價","最低價","收盤價",
                             "漲跌(+/-)","漲跌價差"],
                   "data":[[str(1100+i),"A","1,000","1","10,000","10.0","11.0","9.0","10.5","+","0.5"]
                           for i in range(500)]}]
    }


def tpex_table(date_str="1151030"):
    return {
        "stat":"ok","date":date_str,
        "tables":[{"fields":["代號","名稱","收盤 ","漲跌","開盤 ","最高 ","最低",
                             "成交股數  "," 成交金額(元)"," 成交筆數 "],
                   "data":[[str(5000+i),"B","25.5","0.5","25","26","24",
                            "1,000","25,500","10"] for i in range(400)]}]
    }


def test_twse_dated_official_stock_table_with_ohlcv():
    rows=_validated_market_table(twse_table(),market="TWSE",session=date(2026,10,30))
    assert len(rows)==500
    assert rows[0]["volume"]==1000
    assert rows[0]["date"]=="2026-10-30"
    assert rows[0]["corporate_action_checked"] is False


def test_tpex_no1430_fields_are_stripped():
    rows=_validated_market_table(tpex_table(),market="TPEx",session=date(2026,10,30))
    assert len(rows)==400
    assert rows[0]["turnover"]==25500


def test_stale_date_response_is_hard_failure():
    with pytest.raises(ValueError,match="stale/wrong day"):
        _validated_market_table(tpex_table(date_str="1151103"),market="TPEx",session=date(2026,10,30))


def test_duplicate_stock_codes_rejected():
    p=twse_table()
    p["tables"][0]["data"][1][0]=p["tables"][0]["data"][0][0]
    with pytest.raises(ValueError,match="duplicate"):
        _validated_market_table(p,market="TWSE",session=date(2026,10,30))
