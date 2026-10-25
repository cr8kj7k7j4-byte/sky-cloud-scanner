from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from research.intraday_replay_validator import validate_replay_frame

FORBIDDEN_DECISION_FEATURE_TOKENS = {
    "actual_exit","gross_pnl_twd","net_pnl_twd","r_multiple","mae_r","mfe_r",
    "exit_reason","net_r_045","net_r_065",
}

def _share(df: pd.DataFrame, cols: list[str]) -> float:
    if df.empty or not all(c in df.columns for c in cols):
        return 0.0
    return float(df[cols].notna().all(axis=1).mean())

def _pit_share(df: pd.DataFrame) -> float:
    if df.empty or "pit_universe_member" not in df.columns:
        return 0.0
    return float(df["pit_universe_member"].map(
        lambda x: str(x).strip().lower() in {"true","1"}
    ).mean())

def leakage_audit(df: pd.DataFrame) -> dict:
    reasons=[]
    if df.empty:
        reasons.append("EMPTY_DATASET")

    feature_ts=pd.to_datetime(df.get("feature_cutoff_timestamp"),errors="coerce",utc=True)
    decision_ts=pd.to_datetime(df.get("decision_timestamp"),errors="coerce",utc=True)
    if len(df):
        valid=feature_ts.notna() & decision_ts.notna() & (feature_ts<=decision_ts)
        timestamp_violations=int((~valid).sum())
    else:
        timestamp_violations=0
    if timestamp_violations:
        reasons.append("FEATURE_AFTER_DECISION")

    outcome_before=0
    if "outcome_timestamp" in df.columns:
        out_ts=pd.to_datetime(df["outcome_timestamp"],errors="coerce",utc=True)
        known=out_ts.notna() & decision_ts.notna()
        outcome_before=int((known & (out_ts<decision_ts)).sum())
        if outcome_before:
            reasons.append("OUTCOME_BEFORE_DECISION")

    if "feature_source_columns" in df.columns:
        for raw in df["feature_source_columns"].dropna().astype(str):
            tokens={x.strip() for x in raw.split(",") if x.strip()}
            if tokens & FORBIDDEN_DECISION_FEATURE_TOKENS:
                reasons.append("OUTCOME_FIELD_REFERENCED_BY_FEATURE")
                break

    spread_zero_unknown=0
    if {"spread_bps","execution_context_status"}.issubset(df.columns):
        status=df["execution_context_status"].astype(str).str.upper()
        spread=pd.to_numeric(df["spread_bps"],errors="coerce")
        spread_zero_unknown=int(
            ((status.isin(["MISSING","UNKNOWN","BLOCKED"])) & spread.eq(0)).sum()
        )
        if spread_zero_unknown:
            reasons.append("UNKNOWN_SPREAD_IMPUTED_ZERO")

    future_sector=0
    if {"sector_effective_from","session_date"}.issubset(df.columns):
        sess=pd.to_datetime(df["session_date"],errors="coerce")
        start=pd.to_datetime(df["sector_effective_from"],errors="coerce")
        future_sector=int((start.notna() & sess.notna() & (start>sess)).sum())
        if future_sector:
            reasons.append("FUTURE_SECTOR_MAPPING")

    return {
        "status":"PASS" if not reasons else "FAIL",
        "reasons":sorted(set(reasons)),
        "timestamp_causality_violations":timestamp_violations,
        "outcome_before_decision_violations":outcome_before,
        "unknown_spread_zero_imputations":spread_zero_unknown,
        "future_sector_mapping_violations":future_sector,
    }

def coverage_audit(df: pd.DataFrame) -> dict:
    return {
        "pit_universe":_pit_share(df),
        "market_context":_share(df,["market_regime","market_return","market_breadth","market_volatility"]),
        "sector_mapping":_share(df,["sector","sector_effective_from"]),
        "sector_rs_price":_share(df,["sector_return","sector_rs_vs_market","stock_rs_vs_sector"]),
        "phase_anti_chase":_share(df,[
            "cumulative_vwap","price_vs_vwap_pct","atr14","price_extension_atr",
            "rvol","session_position","stop_distance_pct","phase",
        ]),
        "outcome":_share(df,["r_multiple","mae_r","mfe_r","holding_minutes","outcome_type"]),
        "cost_primary_045":_share(df,["net_r_045"]),
        "cost_stress_065":_share(df,["net_r_065"]),
    }

def audit_frame(df: pd.DataFrame) -> tuple[dict,pd.DataFrame]:
    leakage=leakage_audit(df)
    audited=df.copy()
    if leakage["status"]=="PASS":
        audited["leakage_audit_status"]="PASS"

    contract=validate_replay_frame(audited)
    coverage=coverage_audit(audited)
    thresholds={
        "pit_universe":0.95,
        "market_context":0.95,
        "sector_mapping":0.95,
        "sector_rs_price":0.95,
        "phase_anti_chase":0.95,
        "outcome":0.95,
        "cost_primary_045":1.0,
        "cost_stress_065":1.0,
    }
    blockers=list(contract["reasons"])
    for key,value in coverage.items():
        if value<thresholds[key]:
            blockers.append(f"COVERAGE_FAIL:{key}:{value:.6f}")
    if leakage["status"]!="PASS":
        blockers += [f"LEAKAGE:{x}" for x in leakage["reasons"]]
    if "cost_scenario_status" in audited.columns:
        cost_status = audited["cost_scenario_status"].astype(str).str.upper()
        if (cost_status == "CONFLICT").any():
            blockers.append("COST_SCENARIO_CONFLICT")

    oos_present=(
        "research_split" in audited.columns
        and (audited["research_split"].astype(str).str.upper()=="OOS").any()
    )
    if not oos_present:
        blockers.append("OOS_SPLIT_MISSING")

    blockers=sorted(set(blockers))
    report={
        "gate":"PASS" if not blockers else "DATA_BLOCKED",
        "row_count":int(len(audited)),
        "coverage":{k:round(v,6) for k,v in coverage.items()},
        "coverage_thresholds":thresholds,
        "leakage_audit":leakage,
        "timestamp_causality_audit":{
            "violations":leakage["timestamp_causality_violations"],
            "status":"PASS" if leakage["timestamp_causality_violations"]==0 else "FAIL",
        },
        "w2_contract_validation":contract,
        "oos_present":bool(oos_present),
        "cost_scenario_conflicts": int((audited["cost_scenario_status"].astype(str).str.upper()=="CONFLICT").sum()) if "cost_scenario_status" in audited.columns else 0,
        "blockers":blockers,
        "production_change":False,
    }
    return report,audited

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dataset",required=True)
    ap.add_argument("--out",default="research_output/w3a_intraday_pit/audit.json")
    ap.add_argument("--audited-dataset-out")
    args=ap.parse_args()

    df=pd.read_csv(args.dataset)
    report,audited=audit_frame(df)
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    if args.audited_dataset_out:
        p=Path(args.audited_dataset_out)
        p.parent.mkdir(parents=True,exist_ok=True)
        audited.to_csv(p,index=False)

    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
