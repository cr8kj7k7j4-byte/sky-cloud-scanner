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


def _json(base: Path, rel: str) -> dict:
    p=base/rel
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _historical_universe_status(base: Path) -> str:
    p=base/"research/HISTORICAL_UNIVERSE_AUDIT_20261025.md"
    if not p.exists():
        return "UNKNOWN"
    text=p.read_text(encoding="utf-8",errors="ignore")
    return "PASS" if "Historical Universe Gate: **PASS" in text else "UNKNOWN"


def _diagnostic_5m(base: Path) -> dict:
    obj=_json(base,"research/INTRADAY_5M_SOURCE_COVERAGE_AUDIT_20261025.json")
    if not obj:
        return {"status":"UNKNOWN"}
    return {
        "status":obj.get("formal_gate",{}).get("status","UNKNOWN"),
        "symbols":obj.get("source",{}).get("symbols"),
        "bars":obj.get("source",{}).get("total_bars"),
        "date_from":obj.get("source",{}).get("date_from"),
        "date_to":obj.get("source",{}).get("date_to"),
        "maximum_symbol_coverage_upper_bound":obj.get("maximum_symbol_coverage_upper_bound"),
        "survivorship_bias_warning":obj.get("source",{}).get("survivorship_bias_warning"),
        "workflow_run_id":obj.get("source",{}).get("workflow_run_id"),
        "promotion_grade":False,
    }


def _sector_source_status(base: Path) -> dict:
    registry=_json(base,"research/SECTOR_MEMBERSHIP_PIT_SOURCE_REGISTRY_20261025.json")
    if not registry:
        registry=_json(base,"research/sector_change_source_registry_2023_2026.json")
    if not registry:
        return {"status":"UNKNOWN","gaps":[]}

    gaps=[]
    if "required_but_unverified" in registry:
        gaps=list(registry.get("required_but_unverified") or [])
        status="PASS" if not gaps and registry.get("gate")!="DATA_BLOCKED" else "BLOCKED"
    else:
        for exchange,item in (registry.get("exchanges") or {}).items():
            for year,row in (item.get("years") or {}).items():
                if str(row.get("status")) not in {"VERIFIED","VERIFIED_OFFICIAL","VERIFIED_SOURCE_URL_PENDING_PARSER"}:
                    gaps.append({"exchange":exchange,"year":year,"status":row.get("status")})
        status="PASS" if not gaps else "BLOCKED"
    return {"status":status,"gaps":gaps,"registry":registry}


def _frozen_alpha_status(base: Path) -> dict:
    registry=_json(base,"research/SKY_DAY_V14_FROZEN_RULE_SOURCE_REGISTRY.json")
    if not registry:
        return {"status":"UNKNOWN","unresolved":[]}
    allowed={"FROZEN_CANONICAL_IMPLEMENTATION","HISTORICAL_SNAPSHOT"}
    unresolved=[
        x.get("rule")
        for x in (registry.get("rules") or [])
        if str(x.get("status")) not in allowed
    ]
    return {
        "status":"PASS" if registry.get("rules") and not unresolved else "FROZEN_ALPHA_INPUT_REQUIRED",
        "unresolved":unresolved,
        "strategy_id":registry.get("strategy_id"),
    }


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
    evidence=_json(base,"research/INTRADAY_PIT_SOURCE_EVIDENCE_20261025.json")
    diagnostic_5m=_diagnostic_5m(base)
    sector=_sector_source_status(base)
    frozen=_frozen_alpha_status(base)

    whole=evidence.get("whole_universe_intraday") or {}
    whole_status=str(whole.get("status") or "UNKNOWN").upper()
    benchmark=evidence.get("taiex_benchmark") or {}
    benchmark_status=str(benchmark.get("status") or "UNKNOWN").upper()

    capabilities={
        "historical_universe_2023_plus":pit_status,
        "whole_universe_intraday":whole,
        "taiex_benchmark":benchmark,
        "sector_source_coverage":sector,
        "frozen_v14_alpha":frozen,
        "diagnostic_100_symbol_5m":diagnostic_5m,
        "decision_primitives_builder":(base/"research/build_intraday_decision_primitives.py").exists(),
        "stock_return_cross_section_builder":(base/"research/build_intraday_stock_return_snapshots.py").exists(),
        "sector_rs_context_builder":(base/"research/build_intraday_sector_rs_context.py").exists(),
        "counterfactual_outcome_builder":(base/"research/build_intraday_counterfactual_outcomes.py").exists(),
        "fixed_cost_scenarios":(base/"research/intraday_pit_costs.py").exists(),
        "w2_fail_closed_validator":(base/"research/intraday_replay_validator.py").exists(),
        "w2_runner":(base/"research/w2_intraday_validation_runner.py").exists(),
        "canonical_v2_orchestrator":(base/"research/run_intraday_pit_replay_pipeline.py").exists(),
        "coverage_leakage_timestamp_auditor":(base/"research/audit_intraday_pit_replay.py").exists(),
    }

    blockers=[]
    if pit_status!="PASS" and not inputs["pit_intervals"]["exists"]:
        blockers.append("PIT_UNIVERSE_NOT_READY")

    if whole_status!="PASS":
        blockers.append(
            "PENDING_OR_BLOCKED:SYNCHRONIZED_WHOLE_UNIVERSE_INTRADAY_HISTORY"
            if whole_status in {"IN_PROGRESS","UNKNOWN"}
            else "EXTERNAL_DATA_REQUIRED:SYNCHRONIZED_WHOLE_UNIVERSE_INTRADAY_HISTORY"
        )

    if benchmark_status!="PASS":
        blockers.append("MARKET_BENCHMARK_NOT_READY")

    if sector["status"]!="PASS":
        blockers.append("EXTERNAL_DATA_REQUIRED:EFFECTIVE_DATED_HISTORICAL_SECTOR_MEMBERSHIP")

    if frozen["status"]!="PASS":
        blockers.append("FROZEN_ALPHA_INPUT_REQUIRED:CANONICAL_V14_DECISION_REPLAY")

    if not inputs["decision_stream"]["exists"]:
        blockers.append("NO_HISTORICAL_CANONICAL_DECISION_STREAM")
    if not inputs["ranking_context"]["exists"]:
        blockers.append("NO_FULL_HISTORICAL_CANDIDATE_POOL_RANKING_CONTEXT")
    if not inputs["execution_context"]["exists"]:
        blockers.append("NO_FROZEN_V14_PLANNED_EXECUTION_CONTEXT")

    # Counterfactual outcomes are an engineering-ready derived layer, but cannot
    # exist canonically before frozen decision/execution inputs and source bars.
    if not inputs["outcomes"]["exists"]:
        blockers.append("OUTCOME_JOIN_INPUT_NOT_YET_MATERIALIZED")

    # Empirical L1 is deliberately independent of the fixed 0.45/0.65 stress layer.
    blockers.append("EMPIRICAL_EXECUTION_EVIDENCE_INCOMPLETE")

    dataset_available=inputs["decision_stream"]["exists"]
    audit_state="NOT_EVALUABLE" if not dataset_available else "PENDING_EXECUTION"
    unique_blockers=list(dict.fromkeys(blockers))

    return {
        "issue":81,
        "status":"READY_FOR_W2" if not unique_blockers else "DATA_BLOCKED",
        "w2_readiness_gate":"PASS" if not unique_blockers else "DATA_BLOCKED",
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
        "blockers":unique_blockers,
        "highest_priority_blocker":unique_blockers[0] if unique_blockers else None,
        "governance":{
            "production_change":False,
            "w2_efficacy_allowed":not unique_blockers,
            "fail_closed":True,
            "proxy_substitution_allowed":False,
            "research_only_strategy_may_substitute_for_v14":False,
            "current_sector_backfill_allowed":False,
            "current_universe_backward_sampling_allowed":False,
        },
        "note":(
            "Readiness is evidence-driven. Diagnostic 100-symbol history is never "
            "promotion-grade. Engineering-ready derived layers remain blocked until "
            "their frozen decision-time inputs and source evidence exist."
        ),
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
