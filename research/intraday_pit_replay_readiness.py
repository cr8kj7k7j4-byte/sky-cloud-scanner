from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_INPUTS = {
    "decision_stream":"research_data/intraday_pit/decisions.csv",
    "pit_intervals":"research_data/intraday_pit/pit_intervals.json",
    "market_context":"research_data/intraday_pit/market_context.csv",
    "sector_context":"research_data/intraday_pit/sector_context.csv",
    "feature_context":"research_data/intraday_pit/feature_context.csv",
    "ranking_context":"research_data/intraday_pit/ranking_context.csv",
    "execution_context":"research_data/intraday_pit/execution_context.csv",
    "outcomes":"research_data/intraday_pit/outcomes.csv",
}

def _historical_universe_status(base: Path) -> str:
    p=base/"research/HISTORICAL_UNIVERSE_AUDIT_20261025.md"
    if not p.exists():
        return "UNKNOWN"
    text=p.read_text(encoding="utf-8",errors="ignore")
    return "PASS" if "Historical Universe Gate: **PASS" in text else "UNKNOWN"

def _existing_5m_audit(base: Path) -> dict:
    p=base/"research/INTRADAY_5M_SOURCE_COVERAGE_AUDIT_20261025.json"
    if not p.exists():
        return {"status":"UNKNOWN"}
    try:
        obj=json.loads(p.read_text(encoding="utf-8"))
        return {
            "status":obj.get("formal_gate",{}).get("status","UNKNOWN"),
            "symbols":obj.get("source",{}).get("symbols"),
            "bars":obj.get("source",{}).get("total_bars"),
            "date_from":obj.get("source",{}).get("date_from"),
            "date_to":obj.get("source",{}).get("date_to"),
            "maximum_symbol_coverage_upper_bound":obj.get("maximum_symbol_coverage_upper_bound"),
            "survivorship_bias_warning":obj.get("source",{}).get("survivorship_bias_warning"),
            "workflow_run_id":obj.get("source",{}).get("workflow_run_id"),
        }
    except Exception:
        return {"status":"UNKNOWN"}

def _source_evidence(base: Path) -> dict:
    p=base/"research/INTRADAY_PIT_SOURCE_EVIDENCE_20261025.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def inspect(root: str=".") -> dict:
    base=Path(root)
    inputs={}
    for key,rel in REQUIRED_INPUTS.items():
        p=base/rel
        inputs[key]={
            "path":rel,
            "exists":p.exists(),
            "bytes":p.stat().st_size if p.exists() else 0,
        }

    pit_status=_historical_universe_status(base)
    source_evidence=_source_evidence(base)
    existing_5m=_existing_5m_audit(base)
    capabilities={
        "historical_universe_2023_plus":pit_status,
        "taiex_benchmark":source_evidence.get("taiex_benchmark",{}),
        "current_sector_anchor":source_evidence.get("current_sector_anchor",{}),
        "whole_universe_intraday":source_evidence.get("whole_universe_intraday",{}),
        "frozen_v14_alpha":source_evidence.get("frozen_v14_alpha",{}),
        "historical_5m_export_tooling":(
            (base/"research/download_intraday.py").exists()
            and (base/".github/workflows/export-history-5m.yml").exists()
        ),
        "existing_5m_artifact_audit":existing_5m,
        "sector_rs_replay_module":(base/"src/sector_rs_replay.py").exists(),
        "vwap_entry_replay_module":(base/"src/vwap_entry_replay.py").exists(),
        "execution_engine":(base/"src/execution_engine.py").exists(),
        "w2_fail_closed_validator":(base/"research/intraday_replay_validator.py").exists(),
        "canonical_builder":(base/"research/build_intraday_pit_replay.py").exists(),
        "coverage_leakage_timestamp_auditor":(base/"research/audit_intraday_pit_replay.py").exists(),
    }

    blockers=[]
    if not inputs["sector_context"]["exists"]:
        blockers.append("EXTERNAL_DATA_REQUIRED:EFFECTIVE_DATED_HISTORICAL_SECTOR_MEMBERSHIP")
    if existing_5m.get("status")!="PASS":
        blockers.append("EXTERNAL_DATA_REQUIRED:SYNCHRONIZED_WHOLE_UNIVERSE_INTRADAY_HISTORY")
    if not inputs["decision_stream"]["exists"]:
        blockers.append("EXTERNAL_DATA_REQUIRED:HISTORICAL_DECISION_STREAM_OR_DETERMINISTIC_ALL_CANDIDATE_REPLAY")
    if not inputs["outcomes"]["exists"]:
        blockers.append("EXTERNAL_DATA_REQUIRED:CANONICAL_OUTCOME_JOIN")
    if not inputs["execution_context"]["exists"]:
        blockers.append("FROZEN_ALPHA_INPUT_REQUIRED:PLANNED_EXECUTION_CONTEXT")
    for key in ("market_context","feature_context","ranking_context"):
        if not inputs[key]["exists"]:
            blockers.append(f"MISSING_CANONICAL_INPUT:{key}")
    if pit_status!="PASS" and not inputs["pit_intervals"]["exists"]:
        blockers.append("PIT_UNIVERSE_NOT_READY")

    dataset_available=inputs["decision_stream"]["exists"]
    audit_state="NOT_EVALUABLE" if not dataset_available else "PENDING_EXECUTION"

    return {
        "issue":81,
        "status":"READY_TO_BUILD" if not blockers else "DATA_BLOCKED",
        "w2_readiness_gate":"PASS" if not blockers else "DATA_BLOCKED",
        "source_capabilities":capabilities,
        "inputs":inputs,
        "audits":{
            "coverage_audit":{
                "status":audit_state,
                "reason":None if dataset_available else "NO_CANONICAL_REPLAY_DATASET",
            },
            "leakage_audit":{
                "status":audit_state,
                "reason":None if dataset_available else "NO_CANONICAL_REPLAY_DATASET",
            },
            "timestamp_causality_audit":{
                "status":audit_state,
                "reason":None if dataset_available else "NO_CANONICAL_REPLAY_DATASET",
            },
        },
        "blockers":blockers,
        "highest_priority_blocker":blockers[0] if blockers else None,
        "governance":{
            "production_change":False,
            "w2_efficacy_allowed":not blockers,
            "fail_closed":True,
            "proxy_substitution_allowed":False,
            "empirical_spread_slippage_required_only_when_genuinely_available":True,
        },
        "note":"Missing promotion-grade external historical evidence keeps row-level audits NOT_EVALUABLE and W2 DATA_BLOCKED. Existing 100-symbol current-universe 5m history is diagnostic only and cannot satisfy whole-universe PIT coverage.",
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=".")
    ap.add_argument("--out",default="research_output/w3a_intraday_pit/readiness.json")
    args=ap.parse_args()
    report=inspect(args.root)
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
