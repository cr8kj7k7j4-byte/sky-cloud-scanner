from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from research.intraday_replay_validator import (
    CANONICAL_RULE_COLUMNS,
    IDENTITY_COLUMNS,
    GOVERNANCE_COLUMNS,
    OUTCOME_COLUMNS,
    validate_replay_frame,
)
from src.point_in_time_universe import universe_as_of

DATASET_VERSION = "W3A-INTRADAY-PIT-REPLAY-1.0.0"

DECISION_CONTEXT_COLUMNS = [
    "market_regime","market_return","market_breadth","market_volatility",
    "sector","sector_effective_from","sector_effective_to","sector_return",
    "sector_rs_vs_market","stock_rs_vs_sector",
    "mtf_short_state","mtf_mid_state","mtf_long_state","phase",
    "setup_id","trigger_id","trigger_price","trigger_timestamp","trigger_quality",
    "cumulative_vwap","price_vs_vwap_pct","vwap_slope","day_return_pct","gap_pct",
    "atr14","price_extension_atr","breakout_bar_atr","rvol","volume_zscore",
    "session_low_at_decision","session_high_at_decision","session_position",
    "resistance_distance_pct","stop_distance_pct","stop_distance_atr","spread_bps",
    "price","volume","turnover_twd","liquidity_bucket","spread_bucket",
    "candidate_pool_id","candidate_pool_size","rank_score","ranking_position",
    "ranking_decile","ranking_model_version",
    "planned_entry","planned_stop","planned_target_1","planned_target_2",
    "gross_rr","fee_tax_adjusted_rr","execution_adjusted_rr","fill_probability",
    "expected_entry_slippage_bps","expected_exit_slippage_bps","expected_spread_bps",
    "liquidity_penalty_bps",
]

OUTCOME_JOIN_COLUMNS = [
    "outcome_status","fill_status","actual_entry","actual_exit",
    "actual_entry_slippage_bps","actual_exit_slippage_bps",
    "fees_twd","tax_twd","gross_pnl_twd","net_pnl_twd","r_multiple","mae_r","mfe_r",
    "holding_minutes","false_breakout","missed_entry","exit_reason","outcome_type",
    "outcome_timestamp","net_r_045","net_r_065",
]

def _load_csv(path: str | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    p=Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)

def _load_intervals(path: str | None) -> list[dict]:
    if not path or not Path(path).exists():
        return []
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    return list(obj.get("intervals") or obj)

def _merge_by_decision(base: pd.DataFrame, frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    out=base.copy()
    for frame in frames:
        if frame is None or frame.empty:
            continue
        if "decision_id" not in frame.columns:
            raise ValueError("context frame missing decision_id")
        keep=["decision_id"]+[c for c in frame.columns if c!="decision_id" and c not in out.columns]
        out=out.merge(frame[keep],on="decision_id",how="left",validate="one_to_one")
    return out

def attach_pit_membership(df: pd.DataFrame, intervals: list[dict]) -> pd.DataFrame:
    out=df.copy()
    if out.empty:
        return out
    if not intervals:
        out["pit_universe_member"]=False
        out["universe_source"]="MISSING"
        out["universe_effective_from"]=pd.NA
        out["universe_effective_to"]=pd.NA
        return out

    by_date={}
    interval_index={}
    for d in sorted(set(out["session_date"].astype(str))):
        rows=universe_as_of(intervals,d)
        by_date[d]={(r["exchange"],str(r["symbol"])) for r in rows}
        for r in rows:
            interval_index[(d,r["exchange"],str(r["symbol"]))]=r

    members=[]; sources=[]; starts=[]; ends=[]
    for _,r in out.iterrows():
        d=str(r["session_date"]); ex=str(r["exchange"]); sym=str(r["symbol"])
        item=interval_index.get((d,ex,sym))
        members.append(item is not None)
        sources.append(item.get("source") if item else "MISSING")
        starts.append(item.get("listed_from") if item else pd.NA)
        ends.append(item.get("listed_to") if item else pd.NA)
    out["pit_universe_member"]=members
    out["universe_source"]=sources
    out["universe_effective_from"]=starts
    out["universe_effective_to"]=ends
    return out

def derive_governance_status(df: pd.DataFrame) -> pd.DataFrame:
    out=df.copy()
    if out.empty:
        return out

    market=["market_regime","market_return","market_breadth","market_volatility"]
    sector=["sector","sector_return","sector_rs_vs_market","stock_rs_vs_sector"]
    execution=["planned_entry","planned_stop","planned_target_1","gross_rr","execution_adjusted_rr"]
    required_phase=["cumulative_vwap","price_vs_vwap_pct","atr14","price_extension_atr","rvol","session_position","stop_distance_pct","phase"]

    def status(cols):
        present=[c for c in cols if c in out.columns]
        if len(present)!=len(cols):
            return pd.Series(["MISSING"]*len(out),index=out.index)
        return pd.Series(
            out[cols].notna().all(axis=1).map({True:"OK",False:"MISSING"}).values,
            index=out.index,
        )

    out["market_context_status"]=status(market)
    out["sector_mapping_status"]=status(sector)
    out["execution_context_status"]=status(execution)
    phase_ok=status(required_phase).eq("OK")
    rule_ok=out[[c for c in CANONICAL_RULE_COLUMNS if c in out.columns]].notna().all(axis=1) if all(c in out.columns for c in CANONICAL_RULE_COLUMNS) else False
    out["data_quality_status"]=pd.Series(phase_ok,index=out.index).map({True:"OK",False:"MISSING"})
    out["replay_coverage_status"]=(
        out["market_context_status"].eq("OK")
        & out["sector_mapping_status"].eq("OK")
        & out["execution_context_status"].eq("OK")
        & phase_ok
        & pd.Series(rule_ok,index=out.index)
    ).map({True:"OK",False:"MISSING"})
    if "leakage_audit_status" not in out.columns:
        out["leakage_audit_status"]="UNKNOWN"
    return out

def build_replay(
    decisions: pd.DataFrame,
    *,
    pit_intervals: list[dict],
    context_frames: Iterable[pd.DataFrame]=(),
    outcomes: pd.DataFrame | None=None,
) -> tuple[pd.DataFrame,dict]:
    if decisions.empty:
        return decisions.copy(), {
            "dataset_version":DATASET_VERSION,
            "status":"DATA_BLOCKED",
            "blockers":["MISSING_DECISION_STREAM"],
            "rows":0,
        }

    missing=sorted(set(IDENTITY_COLUMNS)-set(decisions.columns))
    if missing:
        return decisions.copy(), {
            "dataset_version":DATASET_VERSION,
            "status":"DATA_BLOCKED",
            "blockers":[f"MISSING_DECISION_COLUMNS:{','.join(missing)}"],
            "rows":int(len(decisions)),
        }

    df=_merge_by_decision(decisions,context_frames)
    df=attach_pit_membership(df,pit_intervals)
    if outcomes is not None and not outcomes.empty:
        df=_merge_by_decision(df,[outcomes])
    for c in OUTCOME_JOIN_COLUMNS:
        if c not in df.columns:
            df[c]=pd.NA
    df=derive_governance_status(df)

    audit=validate_replay_frame(df)
    manifest={
        "dataset_version":DATASET_VERSION,
        "status":"PASS" if audit["gate"]=="PASS" else "DATA_BLOCKED",
        "rows":int(len(df)),
        "symbols":int(df["symbol"].astype(str).nunique()) if "symbol" in df.columns else 0,
        "period_start":str(df["session_date"].min()) if "session_date" in df.columns and len(df) else None,
        "period_end":str(df["session_date"].max()) if "session_date" in df.columns and len(df) else None,
        "w2_contract_gate":audit["gate"],
        "blockers":audit["reasons"],
    }
    return df,manifest

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--decisions",required=True)
    ap.add_argument("--pit-intervals",required=True)
    ap.add_argument("--market-context")
    ap.add_argument("--sector-context")
    ap.add_argument("--feature-context")
    ap.add_argument("--ranking-context")
    ap.add_argument("--execution-context")
    ap.add_argument("--outcomes")
    ap.add_argument("--out-dir",default="research_output/intraday_pit_replay")
    args=ap.parse_args()

    decisions=_load_csv(args.decisions)
    contexts=[
        _load_csv(args.market_context),_load_csv(args.sector_context),
        _load_csv(args.feature_context),_load_csv(args.ranking_context),
        _load_csv(args.execution_context),
    ]
    outcomes=_load_csv(args.outcomes)
    intervals=_load_intervals(args.pit_intervals)
    df,manifest=build_replay(decisions,pit_intervals=intervals,context_frames=contexts,outcomes=outcomes)

    out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
    df.to_csv(out/"canonical_intraday_pit_replay.csv",index=False)
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
