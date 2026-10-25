from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from research.audit_intraday_pit_replay import audit_frame
from research.build_intraday_pit_replay import build_replay
from research.intraday_pit_costs import apply_fixed_cost_scenarios
from research.w2_intraday_validation_runner import run_validation

PIPELINE_VERSION = "W3A_INTRADAY_PIT_PIPELINE_V2_0"

DOMAIN_COLUMNS = {
    "market_context": [
        "market_regime","market_return","market_breadth","market_volatility",
    ],
    "sector_context": [
        "sector","sector_effective_from","sector_effective_to","sector_return",
        "sector_rs_vs_market","stock_rs_vs_sector",
    ],
    "feature_context": [
        "mtf_short_state","mtf_mid_state","mtf_long_state","phase",
        "setup_id","trigger_id","trigger_price","trigger_timestamp","trigger_quality",
        "entry_reference_price","cumulative_vwap","price_vs_vwap_pct","vwap_slope",
        "day_return_pct","gap_pct","atr14","price_extension_atr","breakout_bar_atr",
        "rvol","volume_zscore","session_low_at_decision","session_high_at_decision",
        "session_position","resistance_distance_pct","stop_distance_pct",
        "stop_distance_atr","price","volume","turnover_twd","liquidity_bucket",
        "spread_bps","spread_bucket",
    ],
    "ranking_context": [
        "candidate_pool_id","candidate_pool_size","rank_score","ranking_position",
        "ranking_decile","ranking_model_version",
    ],
    "execution_context": [
        "planned_entry","planned_stop","planned_target_1","planned_target_2",
        "gross_rr","fee_tax_adjusted_rr","execution_adjusted_rr","fill_probability",
        "expected_entry_slippage_bps","expected_exit_slippage_bps",
        "expected_spread_bps","liquidity_penalty_bps",
    ],
    "outcomes": [
        "outcome_status","fill_status","actual_entry","actual_exit",
        "outcome_exit_price","gross_r_multiple","actual_entry_slippage_bps",
        "actual_exit_slippage_bps","fees_twd","tax_twd","gross_pnl_twd","net_pnl_twd",
        "r_multiple","mae_r","mfe_r","holding_minutes","false_breakout","missed_entry",
        "exit_reason","outcome_type","outcome_timestamp","net_r_045","net_r_065",
    ],
}


def _sha256(path: str | None) -> str | None:
    if not path:
        return None
    p=Path(path)
    if not p.exists():
        return None
    h=hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def _read_csv(path: str | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    p=Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def _read_intervals(path: str) -> list[dict]:
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(obj,list):
        return obj
    if isinstance(obj,dict):
        return list(obj.get("intervals") or obj.get("rows") or [])
    return []


def _source_meta(name: str, path: str | None, frame: pd.DataFrame | None = None) -> dict:
    p=Path(path) if path else None
    exists=bool(p and p.exists())
    return {
        "domain":name,
        "path":path,
        "exists":exists,
        "sha256":_sha256(path),
        "rows":int(len(frame)) if frame is not None else None,
        "columns":list(frame.columns) if frame is not None else None,
    }


def _safe_join(base: pd.DataFrame, frame: pd.DataFrame, domain: str) -> pd.DataFrame:
    if frame.empty:
        return base
    if "decision_id" not in frame.columns:
        raise ValueError(f"{domain}: missing decision_id")
    if frame["decision_id"].duplicated().any():
        raise ValueError(f"{domain}: duplicate decision_id")

    out=base.copy()
    idx=frame.set_index("decision_id")
    base_ids=out["decision_id"].astype(str)
    idx.index=idx.index.astype(str)

    for col in frame.columns:
        if col=="decision_id":
            continue
        incoming=base_ids.map(idx[col])
        if col in out.columns:
            existing=out[col]
            both=existing.notna() & incoming.notna()
            mismatch=both & (existing.astype(str)!=incoming.astype(str))
            if mismatch.any():
                raise ValueError(
                    f"{domain}: conflicting values for {col} on "
                    f"{int(mismatch.sum())} decision rows"
                )
            out[col]=existing.where(existing.notna(),incoming)
        else:
            out[col]=incoming
    return out


def _status(df: pd.DataFrame, cols: Iterable[str]) -> pd.Series:
    cols=list(cols)
    if not cols or not all(c in df.columns for c in cols):
        return pd.Series("MISSING",index=df.index,dtype=object)
    return df[cols].notna().all(axis=1).map({True:"OK",False:"MISSING"})


def _derive_domain_statuses(df: pd.DataFrame) -> pd.DataFrame:
    out=df.copy()
    out["market_context_status"]=_status(out,DOMAIN_COLUMNS["market_context"])
    out["sector_mapping_status"]=_status(
        out,["sector","sector_effective_from","sector_return","sector_rs_vs_market","stock_rs_vs_sector"]
    )
    out["execution_context_status"]=_status(
        out,["planned_entry","planned_stop","planned_target_1","gross_rr","execution_adjusted_rr"]
    )

    phase=_status(
        out,["cumulative_vwap","price_vs_vwap_pct","atr14","price_extension_atr",
             "rvol","session_position","stop_distance_pct","phase"]
    )
    rank=_status(out,DOMAIN_COLUMNS["ranking_context"])
    rule_cols=[
        "market_gate","sector_rs_gate","multi_timeframe_gate","phase_gate",
        "setup_gate","trigger_gate","anti_chase_gate","rr_gate",
        "opportunity_ranking_gate","execution_adjustment_gate",
    ]
    rules=_status(out,rule_cols)

    identity=_status(
        out,["decision_id","symbol","decision_timestamp","feature_cutoff_timestamp",
             "strategy_id","strategy_version","research_split"]
    )
    out["data_quality_status"]=(
        identity.eq("OK") & phase.eq("OK") & rank.eq("OK") & rules.eq("OK")
    ).map({True:"OK",False:"MISSING"})
    out["replay_coverage_status"]=(
        out["market_context_status"].eq("OK")
        & out["sector_mapping_status"].eq("OK")
        & out["execution_context_status"].eq("OK")
        & phase.eq("OK")
        & rank.eq("OK")
        & rules.eq("OK")
    ).map({True:"OK",False:"MISSING"})
    if "leakage_audit_status" not in out.columns:
        out["leakage_audit_status"]="UNKNOWN"
    return out


def assemble(
    *,
    decisions: pd.DataFrame,
    pit_intervals: list[dict],
    market_context: pd.DataFrame | None = None,
    sector_context: pd.DataFrame | None = None,
    feature_context: pd.DataFrame | None = None,
    ranking_context: pd.DataFrame | None = None,
    execution_context: pd.DataFrame | None = None,
    outcomes: pd.DataFrame | None = None,
) -> pd.DataFrame:
    base=build_replay(decisions,pit_intervals)
    for name,frame in [
        ("market_context",market_context),
        ("sector_context",sector_context),
        ("feature_context",feature_context),
        ("ranking_context",ranking_context),
        ("execution_context",execution_context),
    ]:
        if frame is not None:
            base=_safe_join(base,frame,name)

    # Outcome is deliberately joined last, after all decision-time context is frozen.
    if outcomes is not None:
        base=_safe_join(base,outcomes,"outcomes")

    base=apply_fixed_cost_scenarios(base)
    base=_derive_domain_statuses(base)
    return base


def run_pipeline(
    *,
    decisions_path: str,
    pit_universe_path: str,
    out_dir: str,
    market_context_path: str | None = None,
    sector_context_path: str | None = None,
    feature_context_path: str | None = None,
    ranking_context_path: str | None = None,
    execution_context_path: str | None = None,
    outcomes_path: str | None = None,
) -> dict:
    decisions=_read_csv(decisions_path)
    intervals=_read_intervals(pit_universe_path)

    frames={
        "market_context":_read_csv(market_context_path),
        "sector_context":_read_csv(sector_context_path),
        "feature_context":_read_csv(feature_context_path),
        "ranking_context":_read_csv(ranking_context_path),
        "execution_context":_read_csv(execution_context_path),
        "outcomes":_read_csv(outcomes_path),
    }

    replay=assemble(
        decisions=decisions,
        pit_intervals=intervals,
        **frames,
    )

    out=Path(out_dir)
    out.mkdir(parents=True,exist_ok=True)
    raw_path=out/"intraday_pit_replay_v2.csv"
    replay.to_csv(raw_path,index=False)

    audit,audited=audit_frame(replay)
    audited_path=out/"intraday_pit_replay_v2_audited.csv"
    audited.to_csv(audited_path,index=False)

    w2=run_validation(audited)
    w2_path=out/"w2_intraday_validation_report.json"
    w2_path.write_text(json.dumps(w2,ensure_ascii=False,indent=2),encoding="utf-8")

    sources=[
        _source_meta("decisions",decisions_path,decisions),
        _source_meta("pit_universe",pit_universe_path,None),
    ]
    for name,path in [
        ("market_context",market_context_path),
        ("sector_context",sector_context_path),
        ("feature_context",feature_context_path),
        ("ranking_context",ranking_context_path),
        ("execution_context",execution_context_path),
        ("outcomes",outcomes_path),
    ]:
        sources.append(_source_meta(name,path,frames[name]))

    lineage={
        "pipeline_version":PIPELINE_VERSION,
        "generated_at":datetime.now().astimezone().isoformat(),
        "code_revision":os.getenv("GITHUB_SHA") or "UNKNOWN",
        "row_grain":"one symbol × one observation_timestamp × one candidate decision",
        "join_key":"decision_id",
        "join_order":[
            "decisions","pit_universe","market_context","sector_context",
            "feature_context","ranking_context","execution_context","outcomes",
            "fixed_cost_scenarios","audit","w2_validation",
        ],
        "outcome_join_after_feature_freeze":True,
        "alpha_logic_modified":False,
        "sources":sources,
    }
    lineage_path=out/"intraday_pit_replay_lineage.json"
    lineage_path.write_text(json.dumps(lineage,ensure_ascii=False,indent=2),encoding="utf-8")

    manifest={
        "schema_version":"2.0",
        "pipeline_version":PIPELINE_VERSION,
        "status":audit["gate"],
        "row_count":int(len(audited)),
        "symbol_count":int(audited["symbol"].astype(str).nunique()) if "symbol" in audited else 0,
        "session_start":str(audited["session_date"].min()) if len(audited) and "session_date" in audited else None,
        "session_end":str(audited["session_date"].max()) if len(audited) and "session_date" in audited else None,
        "research_split_counts":(
            audited["research_split"].astype(str).value_counts().to_dict()
            if "research_split" in audited else {}
        ),
        "audit":audit,
        "w2_final_status":w2.get("w2_final_status"),
        "w2_efficacy_executed":bool(w2.get("ablation_primary_045") is not None),
        "production_change":False,
        "artifacts":{
            "raw_dataset":str(raw_path),
            "audited_dataset":str(audited_path),
            "lineage":str(lineage_path),
            "w2_report":str(w2_path),
        },
    }
    manifest_path=out/"intraday_pit_replay_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"intraday_pit_replay_audit_v2.json").write_text(
        json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    return manifest


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--decisions",required=True)
    ap.add_argument("--pit-universe",required=True)
    ap.add_argument("--market-context")
    ap.add_argument("--sector-context")
    ap.add_argument("--feature-context")
    ap.add_argument("--ranking-context")
    ap.add_argument("--execution-context")
    ap.add_argument("--outcomes")
    ap.add_argument("--out-dir",default="research_output/w3a_intraday_pit_v2")
    args=ap.parse_args()

    report=run_pipeline(
        decisions_path=args.decisions,
        pit_universe_path=args.pit_universe,
        market_context_path=args.market_context,
        sector_context_path=args.sector_context,
        feature_context_path=args.feature_context,
        ranking_context_path=args.ranking_context,
        execution_context_path=args.execution_context,
        outcomes_path=args.outcomes,
        out_dir=args.out_dir,
    )
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
