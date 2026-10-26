from research.collect_swing_pit_daily_v2 import (
    _adjust,
    _factor,
    _index_intervals,
    _interval_for_day,
)

def test_dividend_factor():
    row={"before_price":"100","reference_price":"95"}
    assert _factor("TaiwanStockDividendResult",row)==0.95

def test_capital_reduction_combined_event_prefers_exright_reference():
    row={
      "ClosingPriceonTheLastTradingDay":"100",
      "PostReductionReferencePrice":"80",
      "OpeningReferencePrice":"80",
      "ExrightReferencePrice":"75",
    }
    assert _factor("TaiwanStockCapitalReductionReferencePrice",row)==0.75

def test_split_factor():
    row={"before_price":"100","after_price":"50"}
    assert _factor("TaiwanStockSplitPrice",row)==0.5

def test_par_value_change_factor():
    row={"before_close":"100","after_ref_close":"20"}
    assert _factor("TaiwanStockParValueChange",row)==0.2

def test_event_factor_back_adjusts_only_pre_event_bars():
    raw=[
      {"date":"2024-01-01","open_raw":100.0,"high_raw":101.0,"low_raw":99.0,"close_raw":100.0,"volume":1,"turnover":1},
      {"date":"2024-01-02","open_raw":91.0,"high_raw":92.0,"low_raw":89.0,"close_raw":90.0,"volume":1,"turnover":1},
    ]
    out=_adjust(raw,{"2024-01-02":{"factor":0.9}})
    assert out[0]["close"]==90.0
    assert out[1]["close"]==90.0
    assert out[0]["price_adjustment_factor"]==0.9
    assert out[1]["price_adjustment_factor"]==1.0

def test_market_transfer_identity():
    pit={"intervals":[
      {"symbol":"1234","exchange":"TPEx","listed_from":"2023-01-01","listed_to":"2024-06-30"},
      {"symbol":"1234","exchange":"TWSE","listed_from":"2024-07-01","listed_to":None},
    ]}
    ix=_index_intervals(pit)
    assert _interval_for_day(ix["1234"],"2024-06-30")["exchange"]=="TPEx"
    assert _interval_for_day(ix["1234"],"2024-07-01")["exchange"]=="TWSE"
