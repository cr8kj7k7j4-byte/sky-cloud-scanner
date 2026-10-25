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
    if "Historical Universe Gate: **PASS" in text or "Historical Universe Gate: **PASS for 2023+" in text:
        return "PASS"
    return "UNKNOWN"

def inspect(root: str=".") -> dict:
    base=Path(root)
    inputs={}
    for key,rel in REQUIRED_INPUTS.items():
        p=base/rel
        inputs[key]={"path":rel,"exists":p.exists(),"bytes":p.stat().st_size if p.exists() else 0}

    pit_status=_historical_universe_status(base)
    capabilities={
        "historical_universe_2023_plus":pit_status,
        "historical_5m_export_tooling":(
            (base/"research/download_intraday.py").exists()
            and (base/".github/workflows/export-history-5m.yml").exists()
        ),
        "w2_fail_closed_validator":(base/"research/intraday_replay_validator.py").exists(),
        "canonical_builder":(base/"research/intraday_pit_replay_builder.py").exists(),
        "coverage_leakage_timestamp_auditor":(base/"research/intraday_pit_replay_audit.py").exists(),
    }

    blockers=[]
    if not inputs["sector_context"]["exists"]:
        blockers.append("NO_EFFECTIVE_DATED_HISTORICAL_SECTOR_MAPPING")
    if not inputs["decision_stream"]["exists"]:
        blockers.append("NO_CANONICAL_HISTORICAL_DECISION_STREAM")
    if not inputs["outcomes"]["exists"]:
        blockers.append("NO_CANONICAL_OUTCOME_JOIN_INPUT")
    for key in ("market_context","feature_context","ranking_context","execution_context"):
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
            "coverage_audit":{"status":audit_state,"reason":None if dataset_available else "NO_CANONICAL_REPLAY_DATASET"},
            "leakage_audit":{"status":audit_state,"reason":None if dataset_available else "NO_CANONICAL_REPLAY_DATASET"},
            "timestamp_causality_audit":{"status":audit_state,"reason":None if dataset_available else "NO_CANONICAL_REPLAY_DATASET"},
        },
        "blockers":blockers,
        "highest_priority_blocker":blockers[0] if blockers else None,
        "governance":{
            "production_change":False,
            "w2_efficacy_allowed":not blockers,
            "fail_closed":True,
        },
        "note":"Readiness inventory precedes row-level coverage/leakage/timestamp audits. Missing canonical replay data keeps those audits NOT_EVALUABLE and W2 DATA_BLOCKED.",
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=".")
    ap.add_argument("--out",default="research_output/intraday_pit_replay/readiness.json")
    args=ap.parse_args()
    report=inspect(args.root)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
