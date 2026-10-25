from __future__ import annotations

import pandas as pd

from research.build_effective_sector_mapping import reconstruct_effective_mapping
from research.build_intraday_market_context import build_market_context
from research.collect_current_sector_anchor import parse_rows


def test_sector_mapping_reconstructs_backward_change_chain():
    current=pd.DataFrame([{
        "symbol":"1111","exchange":"TWSE","sector":"New",
        "source":"official","source_as_of":"2026-10-25",
    }])
    changes=pd.DataFrame([
        {
            "symbol":"1111","exchange":"TWSE","effective_date":"2025-06-01",
            "old_sector":"Old","new_sector":"New",
            "source_url":"official-change","published_at":"2025-05-01",
        }
    ])
    mapping,report=reconstruct_effective_mapping(current,changes,window_start="2023-01-01")
    assert report["status"]=="PASS"
    assert len(mapping)==2
    old=mapping[mapping["sector"]=="Old"].iloc[0]
    new=mapping[mapping["sector"]=="New"].iloc[0]
    assert old["effective_from"]=="2023-01-01"
    assert old["effective_to"]=="2025-05-31"
    assert new["effective_from"]=="2025-06-01"


def test_sector_mapping_fails_chain_mismatch_instead_of_guessing():
    current=pd.DataFrame([{"symbol":"1111","exchange":"TWSE","sector":"Current"}])
    changes=pd.DataFrame([{
        "symbol":"1111","exchange":"TWSE","effective_date":"2025-06-01",
        "old_sector":"Old","new_sector":"Different",
    }])
    mapping,report=reconstruct_effective_mapping(current,changes)
    assert report["status"]=="WARN"
    assert report["unresolved"][0]["reason"]=="CHANGE_CHAIN_MISMATCH"
    assert mapping.empty


def test_current_sector_parser_requires_explicit_sector():
    rows=[
        {"公司代號":"1111","公司簡稱":"A","產業別":"半導體業"},
        {"公司代號":"2222","公司簡稱":"B","產業別":""},
    ]
    parsed,missing=parse_rows(rows,"TWSE","official","2026-10-25")
    assert parsed[0]["sector"]=="半導體業"
    assert missing==["2222"]


def test_market_context_passes_only_with_pit_coverage_and_explicit_benchmark():
    decisions=pd.DataFrame([{
        "decision_id":"d1","decision_timestamp":"2026-01-05T09:05:00+08:00",
        "session_date":"2026-01-05",
    }])
    bars=pd.DataFrame([
        {"symbol":"1111","timestamp":"2026-01-05T09:00:00+08:00","open":10,"close":10.1},
        {"symbol":"1111","timestamp":"2026-01-05T09:05:00+08:00","open":10.1,"close":10.2},
        {"symbol":"2222","timestamp":"2026-01-05T09:00:00+08:00","open":20,"close":19.9},
        {"symbol":"2222","timestamp":"2026-01-05T09:05:00+08:00","open":19.9,"close":20.1},
    ])
    pit=[
        {"symbol":"1111","exchange":"TWSE","listed_from":"2020-01-01","listed_to":None},
        {"symbol":"2222","exchange":"TWSE","listed_from":"2020-01-01","listed_to":None},
    ]
    benchmark=pd.DataFrame([{
        "timestamp":"2026-01-05T09:05:00+08:00","market_return":0.001,
    }])
    regime=pd.DataFrame([{"decision_id":"d1","market_regime":"FROZEN_TEST"}])
    frame,report=build_market_context(decisions,bars,pit,benchmark,regime)
    assert report["status"]=="PASS"
    assert report["min_member_coverage"]==1.0
    assert float(frame.loc[0,"market_return"])==0.001


def test_market_context_does_not_substitute_equal_weight_for_missing_benchmark():
    decisions=pd.DataFrame([{
        "decision_id":"d1","decision_timestamp":"2026-01-05T09:05:00+08:00",
        "session_date":"2026-01-05",
    }])
    bars=pd.DataFrame([
        {"symbol":"1111","timestamp":"2026-01-05T09:00:00+08:00","open":10,"close":10.1},
    ])
    pit=[{"symbol":"1111","exchange":"TWSE","listed_from":"2020-01-01","listed_to":None}]
    frame,report=build_market_context(decisions,bars,pit,None)
    assert report["status"]=="BLOCKED"
    assert pd.isna(frame.loc[0,"market_return"])
    assert frame.loc[0,"market_equal_weight_return"] is not None


def test_market_regime_is_never_inferred_by_w3a():
    decisions=pd.DataFrame([{
        "decision_id":"d1","decision_timestamp":"2026-01-05T09:05:00+08:00",
        "session_date":"2026-01-05",
    }])
    bars=pd.DataFrame([
        {"symbol":"1111","timestamp":"2026-01-05T09:00:00+08:00","open":10,"close":10.1},
        {"symbol":"1111","timestamp":"2026-01-05T09:05:00+08:00","open":10.1,"close":10.2},
    ])
    pit=[{"symbol":"1111","exchange":"TWSE","listed_from":"2020-01-01","listed_to":None}]
    benchmark=pd.DataFrame([{
        "timestamp":"2026-01-05T09:05:00+08:00","market_return":0.001,
    }])
    frame,report=build_market_context(decisions,bars,pit,benchmark,None)
    assert report["status"]=="BLOCKED"
    assert report["benchmark_available"] is True
    assert report["frozen_regime_available"] is False
    assert pd.isna(frame.loc[0,"market_regime"])
