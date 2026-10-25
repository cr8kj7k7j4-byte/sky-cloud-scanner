from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pandas as pd

from research.intraday_pit_costs import apply_fixed_cost_scenarios
from research.run_intraday_pit_replay_pipeline import run_pipeline
from research.intraday_replay_validator import CANONICAL_RULE_COLUMNS


def test_fixed_cost_scenarios_convert_round_trip_drag_to_r():
    df=pd.DataFrame([{
        "planned_entry":100.0,
        "planned_stop":99.0,
        "gross_r_multiple":1.0,
    }])
    out=apply_fixed_cost_scenarios(df)
    assert round(float(out.loc[0,"net_r_045"]),6)==0.55
    assert round(float(out.loc[0,"net_r_065"]),6)==0.35
    assert out.loc[0,"cost_scenario_status"]=="OK"


def test_fixed_cost_scenarios_detect_conflicting_supplied_values():
    df=pd.DataFrame([{
        "planned_entry":100.0,
        "planned_stop":99.0,
        "gross_r_multiple":1.0,
        "net_r_045":0.99,
        "net_r_065":0.35,
    }])
    out=apply_fixed_cost_scenarios(df)
    assert out.loc[0,"cost_scenario_status"]=="CONFLICT"
    assert float(out.loc[0,"net_r_045"])==0.99


def _write_complete_inputs(tmp_path):
    tz=timezone(timedelta(hours=8))
    decisions=[]; market=[]; sector=[]; feature=[]; ranking=[]; execution=[]; outcomes=[]
    start=datetime(2026,1,1,9,30,tzinfo=tz)
    n=160
    for i in range(n):
        day=i//2
        ts=start+timedelta(days=day,minutes=(i%2)*5)
        did=f"d{i}"
        d={
            "decision_id":did,
            "run_id":f"r{day}",
            "strategy_id":"sky-day-v14",
            "strategy_version":"1.4",
            "symbol":"2409" if i%2==0 else "3481",
            "exchange":"TWSE",
            "session_date":ts.date().isoformat(),
            "observation_timestamp":ts.isoformat(),
            "feature_cutoff_timestamp":(ts-timedelta(seconds=1)).isoformat(),
            "decision_timestamp":ts.isoformat(),
            "data_timezone":"Asia/Taipei",
            "feature_schema_version":"1.2.0",
            "rule_schema_version":"w2-10-rule-v1",
            "cost_model_version":"W2_FIXED_ROUND_TRIP_045_065_V1",
            "research_split":"OOS",
        }
        for rule in CANONICAL_RULE_COLUMNS:
            d[rule]=True
        decisions.append(d)
        regime=["Bull","Neutral","Bear"][day%3]
        market.append({
            "decision_id":did,"market_regime":regime,
            "market_return":0.01 if regime=="Bull" else (-0.01 if regime=="Bear" else 0.0),
            "market_breadth":0.62 if regime=="Bull" else (0.38 if regime=="Bear" else 0.5),
            "market_volatility":0.02,
        })
        sector.append({
            "decision_id":did,"sector":"Display",
            "sector_effective_from":"2023-01-01","sector_effective_to":None,
            "sector_return":0.012,"sector_rs_vs_market":0.002,
            "stock_rs_vs_sector":0.003,
        })
        feature.append({
            "decision_id":did,
            "mtf_short_state":"UP","mtf_mid_state":"UP","mtf_long_state":"UP",
            "phase":"P3","setup_id":"FROZEN_V14","trigger_id":"T1",
            "trigger_price":12.1,"trigger_timestamp":ts.isoformat(),
            "trigger_quality":"OK","entry_reference_price":12.1,
            "cumulative_vwap":12.0,"price_vs_vwap_pct":0.008333,
            "vwap_slope":0.01,"day_return_pct":1.0,"gap_pct":0.2,
            "atr14":0.5,"price_extension_atr":0.2,"breakout_bar_atr":0.4,
            "rvol":1.5,"volume_zscore":1.0,
            "session_low_at_decision":11.8,"session_high_at_decision":12.2,
            "session_position":0.75,"resistance_distance_pct":1.5,
            "stop_distance_pct":2.4793,"stop_distance_atr":0.6,
            "price":12.1,"volume":1000,"turnover_twd":12100000,
            "liquidity_bucket":"L1","spread_bps":None,"spread_bucket":"UNKNOWN",
        })
        ranking.append({
            "decision_id":did,"candidate_pool_id":f"pool-{day}",
            "candidate_pool_size":2,"rank_score":80.0-(i%2),
            "ranking_position":(i%2)+1,"ranking_decile":(i%2)+1,
            "ranking_model_version":"FROZEN_V14",
        })
        execution.append({
            "decision_id":did,"planned_entry":12.1,"planned_stop":11.8,
            "planned_target_1":12.7,"planned_target_2":13.0,
            "gross_rr":2.0,"fee_tax_adjusted_rr":1.8,
            "execution_adjusted_rr":1.7,"fill_probability":None,
            "expected_entry_slippage_bps":None,"expected_exit_slippage_bps":None,
            "expected_spread_bps":None,"liquidity_penalty_bps":None,
        })
        gross=1.0 if i%3 else -0.5
        outcomes.append({
            "decision_id":did,"outcome_status":"COMPLETE",
            "fill_status":"COUNTERFACTUAL","actual_entry":None,"actual_exit":None,
            "outcome_exit_price":12.1+gross*(12.1-11.8),
            "gross_r_multiple":gross,
            "actual_entry_slippage_bps":None,"actual_exit_slippage_bps":None,
            "fees_twd":None,"tax_twd":None,"gross_pnl_twd":None,"net_pnl_twd":None,
            "r_multiple":gross,"mae_r":-0.2,"mfe_r":1.2,
            "holding_minutes":30,"false_breakout":bool(i%5==0),
            "missed_entry":False,"exit_reason":"HORIZON",
            "outcome_type":"COUNTERFACTUAL",
            "outcome_timestamp":(ts+timedelta(minutes=30)).isoformat(),
        })

    paths={}
    for name,rows in [
        ("decisions",decisions),("market",market),("sector",sector),("feature",feature),
        ("ranking",ranking),("execution",execution),("outcomes",outcomes),
    ]:
        p=tmp_path/f"{name}.csv";pd.DataFrame(rows).to_csv(p,index=False);paths[name]=str(p)
    pit=tmp_path/"pit.json"
    pit.write_text(json.dumps([
        {"symbol":"2409","exchange":"TWSE","name":"A","listed_from":"2020-01-01","listed_to":None,"source":"official"},
        {"symbol":"3481","exchange":"TWSE","name":"B","listed_from":"2020-01-01","listed_to":None,"source":"official"},
    ]),encoding="utf-8")
    paths["pit"]=str(pit)
    return paths


def test_v2_pipeline_builds_audits_and_hands_off_to_w2(tmp_path):
    p=_write_complete_inputs(tmp_path)
    out=tmp_path/"out"
    manifest=run_pipeline(
        decisions_path=p["decisions"],pit_universe_path=p["pit"],
        market_context_path=p["market"],sector_context_path=p["sector"],
        feature_context_path=p["feature"],ranking_context_path=p["ranking"],
        execution_context_path=p["execution"],outcomes_path=p["outcomes"],
        out_dir=str(out),
    )
    assert manifest["status"]=="PASS"
    assert manifest["audit"]["leakage_audit"]["status"]=="PASS"
    assert manifest["audit"]["timestamp_causality_audit"]["violations"]==0
    assert manifest["audit"]["coverage"]["cost_primary_045"]==1.0
    assert manifest["audit"]["coverage"]["cost_stress_065"]==1.0
    assert manifest["w2_efficacy_executed"] is True
    assert (out/"intraday_pit_replay_lineage.json").exists()
    assert (out/"w2_intraday_validation_report.json").exists()


def test_v2_pipeline_fails_closed_when_context_domains_missing(tmp_path):
    p=_write_complete_inputs(tmp_path)
    out=tmp_path/"blocked"
    manifest=run_pipeline(
        decisions_path=p["decisions"],pit_universe_path=p["pit"],
        outcomes_path=p["outcomes"],out_dir=str(out),
    )
    assert manifest["status"]=="DATA_BLOCKED"
    assert manifest["w2_efficacy_executed"] is False
