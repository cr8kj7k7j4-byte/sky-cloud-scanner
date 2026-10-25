from research.collect_swing_pit_daily_v2 import _adjust, _candidate_event_dates, _index_intervals, _interval_for_day

def test_event_factor_back_adjusts_only_pre_event_bars():
    raw=[
      {"date":"2024-01-01","open_raw":100.0,"high_raw":101.0,"low_raw":99.0,"close_raw":100.0,"volume":1,"turnover":1,"spread":0},
      {"date":"2024-01-02","open_raw":91.0,"high_raw":92.0,"low_raw":89.0,"close_raw":90.0,"volume":1,"turnover":1,"spread":0},
    ]
    out=_adjust(raw,{"2024-01-02":{"factor":0.9}})
    assert out[0]["close"]==90.0
    assert out[1]["close"]==90.0

def test_reference_discontinuity_candidate():
    raw=[
      {"date":"2024-01-01","close_raw":100.0,"spread":1.0},
      {"date":"2024-01-02","close_raw":91.0,"spread":1.0},
    ]
    c=_candidate_event_dates(raw)
    assert "2024-01-02" in c
    assert round(c["2024-01-02"]["reference_ratio"],4)==0.9

def test_market_transfer_identity():
    pit={"intervals":[
      {"symbol":"1234","exchange":"TPEx","listed_from":"2023-01-01","listed_to":"2024-06-30"},
      {"symbol":"1234","exchange":"TWSE","listed_from":"2024-07-01","listed_to":None},
    ]}
    ix=_index_intervals(pit)
    assert _interval_for_day(ix["1234"],"2024-06-30")["exchange"]=="TPEx"
    assert _interval_for_day(ix["1234"],"2024-07-01")["exchange"]=="TWSE"
