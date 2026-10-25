from __future__ import annotations

import pandas as pd

from research.build_intraday_stock_return_snapshots import build_stock_return_snapshots
from research.build_intraday_sector_rs_context import build_sector_rs_context


def test_stock_return_snapshots_use_pit_full_cross_section():
    decisions=pd.DataFrame([{
        "decision_id":"d1",
        "decision_timestamp":"2026-01-05T09:05:00+08:00",
        "session_date":"2026-01-05",
        "symbol":"1111",
    }])
    bars=pd.DataFrame([
        {"symbol":"1111","timestamp":"2026-01-05T09:00:00+08:00","session_date":"2026-01-05","open":10.0,"close":10.0},
        {"symbol":"1111","timestamp":"2026-01-05T09:05:00+08:00","session_date":"2026-01-05","open":10.0,"close":11.0},
        {"symbol":"2222","timestamp":"2026-01-05T09:00:00+08:00","session_date":"2026-01-05","open":20.0,"close":20.0},
        {"symbol":"2222","timestamp":"2026-01-05T09:05:00+08:00","session_date":"2026-01-05","open":20.0,"close":19.0},
        {"symbol":"3333","timestamp":"2026-01-05T09:05:00+08:00","session_date":"2026-01-05","open":30.0,"close":99.0},
    ])
    pit=[
        {"symbol":"1111","exchange":"TWSE","listed_from":"2020-01-01","listed_to":None},
        {"symbol":"2222","exchange":"TWSE","listed_from":"2020-01-01","listed_to":None},
    ]
    frame,report=build_stock_return_snapshots(decisions,bars,pit)
    assert report["status"]=="PASS"
    assert set(frame["symbol"])=={"1111","2222"}
    vals=frame.set_index("symbol")["stock_return"].to_dict()
    assert round(vals["1111"],6)==0.1
    assert round(vals["2222"],6)==-0.05


def test_sector_rs_uses_effective_mapping_and_market_benchmark():
    decisions=pd.DataFrame([
        {"decision_id":"d1","symbol":"1111","decision_timestamp":"2026-01-05T09:05:00+08:00"},
        {"decision_id":"d2","symbol":"2222","decision_timestamp":"2026-01-05T09:05:00+08:00"},
    ])
    returns=pd.DataFrame([
        {"observation_timestamp":"2026-01-05T09:05:00+08:00","symbol":"1111","stock_return":0.10},
        {"observation_timestamp":"2026-01-05T09:05:00+08:00","symbol":"2222","stock_return":0.00},
        {"observation_timestamp":"2026-01-05T09:05:00+08:00","symbol":"3333","stock_return":-0.02},
    ])
    mapping=pd.DataFrame([
        {"symbol":"1111","sector":"Semi","effective_from":"2023-01-01","effective_to":None},
        {"symbol":"2222","sector":"Semi","effective_from":"2023-01-01","effective_to":None},
        {"symbol":"3333","sector":"Other","effective_from":"2023-01-01","effective_to":None},
    ])
    market=pd.DataFrame([
        {"decision_id":"d1","market_return":0.01},
        {"decision_id":"d2","market_return":0.01},
    ])
    frame,report=build_sector_rs_context(decisions,returns,mapping,market)
    assert report["status"]=="PASS"
    d1=frame.set_index("decision_id").loc["d1"]
    assert round(float(d1["sector_return"]),6)==0.05
    assert round(float(d1["sector_rs_vs_market"]),6)==0.04
    assert round(float(d1["stock_rs_vs_sector"]),6)==0.05


def test_sector_rs_blocks_incomplete_mapping():
    decisions=pd.DataFrame([
        {"decision_id":"d1","symbol":"1111","decision_timestamp":"2026-01-05T09:05:00+08:00"},
    ])
    returns=pd.DataFrame([
        {"observation_timestamp":"2026-01-05T09:05:00+08:00","symbol":"1111","stock_return":0.10},
        {"observation_timestamp":"2026-01-05T09:05:00+08:00","symbol":"2222","stock_return":0.00},
    ])
    mapping=pd.DataFrame([
        {"symbol":"1111","sector":"Semi","effective_from":"2023-01-01","effective_to":None},
    ])
    market=pd.DataFrame([{"decision_id":"d1","market_return":0.01}])
    _,report=build_sector_rs_context(decisions,returns,mapping,market)
    assert report["status"]=="BLOCKED"
    assert report["cross_section_mapping_coverage"]==0.5
