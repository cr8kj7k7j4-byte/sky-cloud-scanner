from __future__ import annotations

import argparse
import json
from pathlib import Path

CANONICAL_RULE_COLUMNS = [
    "market_gate",
    "sector_rs_gate",
    "multi_timeframe_gate",
    "phase_gate",
    "setup_gate",
    "trigger_gate",
    "anti_chase_gate",
    "rr_gate",
    "opportunity_ranking_gate",
    "execution_adjustment_gate",
]

REQUIRED_EXECUTION_FIELDS = [
    "planned_entry",
    "planned_stop",
    "planned_target_1",
    "gross_rr",
    "execution_adjusted_rr",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8",errors="ignore") if path.exists() else ""


def audit_repo(root: str=".") -> dict:
    base=Path(root)
    src=base/"src"
    production_files=sorted(src.glob("*.py")) if src.exists() else []
    texts={str(p.relative_to(base)):_read(p) for p in production_files}

    rule_owners={}
    for rule in CANONICAL_RULE_COLUMNS:
        owners=[path for path,text in texts.items() if rule in text]
        rule_owners[rule]=owners

    all_rule_outputs_implemented=all(bool(rule_owners[x]) for x in CANONICAL_RULE_COLUMNS)

    main_text=texts.get("src/main.py","")
    top100_truncation=(
        "rank_screening_candidates(passed)[:TOP_N]" in main_text
        or "rank_screening_candidates(passed)[:TOP_N" in main_text
    )
    scanner_writes_top100='"top100"' in main_text
    scanner_writes_deep='"deep"' in main_text

    strategy_text=texts.get("src/strategy_builder.py","")
    strategy_research_only=(
        "research" in strategy_text.lower()
        and "production_eligible" in strategy_text
    )

    executable_v14_candidates=[
        path for path,text in texts.items()
        if ("v1.4" in text or "v14" in text.lower())
        and any(rule in text for rule in CANONICAL_RULE_COLUMNS)
    ]

    required_data_path=base/"research_data/intraday_pit/decisions.csv"
    historical_decision_stream_present=required_data_path.exists() and required_data_path.stat().st_size>0

    blockers=[]
    if not all_rule_outputs_implemented:
        missing=[k for k,v in rule_owners.items() if not v]
        blockers.append("FROZEN_V14_RULE_OUTPUT_PROVIDER_MISSING:"+",".join(missing))
    if not executable_v14_candidates:
        blockers.append("NO_EXECUTABLE_FROZEN_V14_REPLAY_ADAPTER")
    if top100_truncation:
        blockers.append("CURRENT_SCANNER_CANDIDATE_POOL_TRUNCATED_TOP_N")
    if not historical_decision_stream_present:
        blockers.append("NO_HISTORICAL_CANONICAL_DECISION_STREAM")
    if strategy_research_only:
        blockers.append("RESEARCH_ONLY_STRATEGY_BUILDER_NOT_VALID_V14_SUBSTITUTE")

    return {
        "schema_version":"FROZEN_V14_REPLAY_READINESS_V1_0",
        "production_source_files_scanned":len(production_files),
        "canonical_rule_columns":CANONICAL_RULE_COLUMNS,
        "rule_owners":rule_owners,
        "all_rule_outputs_implemented_in_src":all_rule_outputs_implemented,
        "executable_v14_replay_candidates":executable_v14_candidates,
        "historical_decision_stream_present":historical_decision_stream_present,
        "scanner_snapshot":{
            "top100_field_present":scanner_writes_top100,
            "deep_field_present":scanner_writes_deep,
            "candidate_pool_truncated_by_top_n":top100_truncation,
        },
        "strategy_builder_research_only":strategy_research_only,
        "status":"PASS" if not blockers else "FROZEN_ALPHA_INPUT_REQUIRED",
        "blockers":blockers,
        "governance":{
            "research_strategy_may_substitute_for_v14":False,
            "alpha_logic_modified":False,
            "w2_rule_efficacy_allowed":not blockers,
        },
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=".")
    ap.add_argument("--out",default="research_output/frozen_v14_replay_readiness.json")
    args=ap.parse_args()
    report=audit_repo(args.root)
    p=Path(args.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
