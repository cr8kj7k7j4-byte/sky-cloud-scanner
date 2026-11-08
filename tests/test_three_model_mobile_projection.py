import pytest
from research.three_model_mobile_projection import project

def sample():
    return {"signal_id":"abcd","model_id":"next_day","symbol":"1101",
            "stock_name":None,"bar_time":"2026-11-06T13:30:00+08:00",
            "direction":"LONG_WATCH","reference_close":31.5,
            "production_signal":False,"order_authorized":False,
            "trained_model_used":False,"eligible_strategy_trade":False}

def test_mobile_schema_is_not_trading_or_live():
    x=project([sample()])
    assert x["正式交易"] is False and x["即時行情已驗收"] is False
    assert x["CloudRun已部署"] is False
    row=x["rows"][0]
    assert row["股票名稱"]=="待確認"
    assert row["買進觸發"] is None and row["最高接受價"] is None
    assert row["現在動作"]=="觀察"
    assert row["訊號資格"].startswith("研究觀察")
    assert "非盤中即時成交" in row["行情類型"]

@pytest.mark.parametrize("field",[ "production_signal","order_authorized","trained_model_used","eligible_strategy_trade"])
def test_promotion_claims_are_rejected(field):
    row=sample()
    row[field]=True
    with pytest.raises(ValueError):
        project([row])

def test_invalid_models_not_displayed():
    row=sample()
    row["model_id"]="old_archived_strategy"
    assert project([row])["rows"]==[]

def test_rejected_no_trade_record_visible_without_fabricated_bar_time():
    row=sample()
    row.update(signal_id=None, ledger_record_id="rejected-abc",
               direction="NO_TRADE",bar_time=None,
               rejection_reasons=["insufficient_bars"])
    x=project([row])
    assert x["資料健康"]["已標示不交易"]==1
    assert x["資料健康"]["缺行情時間"]==1
    assert x["rows"][0]["現在動作"]=="等待"
    assert x["rows"][0]["行情時間"]=="待確認"
    assert x["rows"][0]["歷史參考收盤價"] is None
    assert x["rows"][0]["拒絕原因"]==["insufficient_bars"]

def test_duplicate_ledger_id_is_rejected_instead_of_double_counting():
    row=sample()
    with pytest.raises(ValueError,match="duplicate_ledger_record_id"):
        project([row,row])

def test_missing_record_id_does_not_silently_disappear():
    row=sample()
    row["signal_id"]=None
    with pytest.raises(ValueError,match="missing_ledger_record_id"):
        project([row])

def test_naive_market_bar_time_is_rejected():
    row=sample()
    row["bar_time"]="2026-11-06T13:30:00"
    with pytest.raises(ValueError,match="timezone_required"):
        project([row])

def test_research_mobile_never_claims_live_or_cloudrun_deployment():
    x=project([sample()])
    assert x["即時行情已驗收"] is False
    assert x["CloudRun已部署"] is False
    assert x["資料健康"]["實際雲端頁面已驗收"] is False
