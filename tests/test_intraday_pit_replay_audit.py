from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from research.audit_intraday_pit_replay import audit_frame
from research.intraday_pit_replay_readiness import inspect
from research.intraday_replay_validator import CANONICAL_RULE_COLUMNS

def make_complete_frame(rows=20):
    base=datetime(2026,1,5,9,30,tzinfo=timezone(timedelta(hours=8)))
    out=[]
    for i in range(rows):
        ts=base+timedelta(minutes=5*i)
        row={
            "decision_id":f"d{i}","run_id":"r1","strategy_id":"sky-day-v14",
            "strategy_version":"1.4","symbol":"2409","exchange":"TWSE",
            "session_date":ts.date().isoformat(),
            "observation_timestamp":ts.isoformat(),
            "feature_cutoff_timestamp":(ts-timedelta(seconds=1)).isoformat(),
            "decision_timestamp":ts.isoformat(),
            "data_timezone":"Asia/Taipei",
            "feature_schema_version":"1.2.0",
            "rule_schema_version":"w2-10-rule-v1",
            "cost_model_version":"cost-v1",
            "research_split":"OOS",
            "pit_universe_member":True,
            "data_quality_status":"OK",
            "leakage_audit_status":"UNKNOWN",
            "market_context_status":"OK",
            "sector_mapping_status":"OK",
            "execution_context_status":"OK",
            "replay_coverage_status":"OK",
            "market_regime":"Bull",
            "market_return":0.01,
            "market_breadth":0.60,
            "market_volatility":0.02,
            "sector":"Display",
            "sector_effective_from":"2023-01-01",
            "sector_effective_to":None,
            "sector_return":0.012,
            "sector_rs_vs_market":0.002,
            "stock_rs_vs_sector":0.003,
            "cumulative_vwap":12.0,
            "price_vs_vwap_pct":0.2,
            "atr14":0.5,
            "price_extension_atr":0.4,
            "rvol":1.5,
            "session_position":0.6,
            "stop_distance_pct":1.2,
            "phase":"P3",
            "candidate_pool_id":"p1",
            "candidate_pool_size":20,
            "rank_score":80-i,
            "ranking_position":i+1,
            "ranking_decile":min(10,i//2+1),
            "ranking_model_version":"rank-v1",
            "planned_entry":12.1,
            "planned_stop":11.8,
            "planned_target_1":12.7,
            "gross_rr":2.0,
            "execution_adjusted_rr":1.7,
            "r_multiple":0.5,
            "mae_r":-0.2,
            "mfe_r":1.0,
            "holding_minutes":30,
            "outcome_type":"COUNTERFACTUAL",
            "outcome_timestamp":(ts+timedelta(minutes=30)).isoformat(),
            "net_r_045":0.5,
            "net_r_065":0.3,
        }
        for c in CANONICAL_RULE_COLUMNS:
            row[c]=True
        out.append(row)
    return pd.DataFrame(out)

def test_full_audit_passes_and_marks_leakage_pass():
    report,audited=audit_frame(make_complete_frame())
    assert report["gate"]=="PASS"
    assert report["leakage_audit"]["status"]=="PASS"
    assert report["timestamp_causality_audit"]["violations"]==0
    assert set(audited["leakage_audit_status"])=={"PASS"}

def test_future_feature_timestamp_blocks():
    df=make_complete_frame()
    df.loc[0,"feature_cutoff_timestamp"]=(
        pd.Timestamp(df.loc[0,"decision_timestamp"])+pd.Timedelta(minutes=1)
    ).isoformat()
    report,_=audit_frame(df)
    assert report["gate"]=="DATA_BLOCKED"
    assert "FEATURE_AFTER_DECISION" in report["leakage_audit"]["reasons"]

def test_unknown_spread_cannot_be_zero():
    df=make_complete_frame()
    df["spread_bps"]=0.0
    df["execution_context_status"]="UNKNOWN"
    report,_=audit_frame(df)
    assert report["gate"]=="DATA_BLOCKED"
    assert "UNKNOWN_SPREAD_IMPUTED_ZERO" in report["leakage_audit"]["reasons"]

def test_future_sector_mapping_blocks():
    df=make_complete_frame()
    df["sector_effective_from"]="2027-01-01"
    report,_=audit_frame(df)
    assert report["gate"]=="DATA_BLOCKED"
    assert "FUTURE_SECTOR_MAPPING" in report["leakage_audit"]["reasons"]

def test_missing_outcome_coverage_blocks():
    df=make_complete_frame()
    df.loc[:5,"mfe_r"]=pd.NA
    report,_=audit_frame(df)
    assert report["gate"]=="DATA_BLOCKED"
    assert any(x.startswith("COVERAGE_FAIL:outcome:") for x in report["blockers"])

def test_repository_readiness_fails_closed_without_inputs(tmp_path):
    report=inspect(str(tmp_path))
    assert report["status"]=="DATA_BLOCKED"
    assert report["w2_readiness_gate"]=="DATA_BLOCKED"
    assert "EXTERNAL_DATA_REQUIRED:EFFECTIVE_DATED_HISTORICAL_SECTOR_MEMBERSHIP" in report["blockers"]
    assert report["audits"]["coverage_audit"]["status"]=="NOT_EVALUABLE"
