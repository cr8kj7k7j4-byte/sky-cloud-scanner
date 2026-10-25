from __future__ import annotations

import argparse
import json
import re
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

ALLOWED_PROVIDER_STATUS={"FROZEN_CANONICAL_IMPLEMENTATION","HISTORICAL_SNAPSHOT"}
METADATA_ONLY_MODULES={"src/model_registry.py"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8",errors="ignore") if path.exists() else ""


def _rule_implementation_candidates(text: str, rule: str) -> bool:
    patterns=[
        rf'["\']{re.escape(rule)}["\']\s*:',
        rf'\b{re.escape(rule)}\s*=',
        rf'def\s+{re.escape(rule)}\s*\(',
        rf'def\s+\w*{re.escape(rule)}\w*\s*\(',
    ]
    return any(re.search(p,text) for p in patterns)


def _formal_registry(base: Path) -> dict:
    p=base/"research/SKY_DAY_V14_FROZEN_RULE_SOURCE_REGISTRY.json"
    if not p.exists():
        return {"exists":False,"rules":[]}
    obj=json.loads(p.read_text(encoding="utf-8"))
    rules=list(obj.get("rules") or [])
    unresolved=[
        x for x in rules
        if str(x.get("status")) not in ALLOWED_PROVIDER_STATUS
    ]
    return {
        "exists":True,
        "strategy_id":obj.get("strategy_id"),
        "rules":rules,
        "resolved_count":len(rules)-len(unresolved),
        "rule_count":len(rules),
        "coverage":round((len(rules)-len(unresolved))/max(len(rules),1),6),
        "unresolved":[x.get("rule") for x in unresolved],
        "status":"PASS" if rules and not unresolved else "BLOCKED",
        "governance":obj.get("governance") or {},
    }


def audit_repo(root: str=".") -> dict:
    base=Path(root)
    formal=_formal_registry(base)

    src=base/"src"
    production_files=sorted(src.glob("*.py")) if src.exists() else []
    texts={str(p.relative_to(base)):_read(p) for p in production_files}

    rule_mentions={}
    rule_implementation_owners={}
    for rule in CANONICAL_RULE_COLUMNS:
        rule_mentions[rule]=[
            path for path,text in texts.items() if rule in text
        ]
        rule_implementation_owners[rule]=[
            path for path,text in texts.items()
            if path not in METADATA_ONLY_MODULES
            and _rule_implementation_candidates(text,rule)
        ]

    model_registry=texts.get("src/model_registry.py","")
    m=re.search(r"CORE_RULE_IDS\s*=\s*\((.*?)\)",model_registry,flags=re.S)
    registry_rules=(
        re.findall(r'["\']([^"\']+)["\']',m.group(1))
        if m else []
    )
    registry_missing=[
        x for x in CANONICAL_RULE_COLUMNS if x not in registry_rules
    ]

    main_text=texts.get("src/main.py","")
    top100_truncation=(
        "rank_screening_candidates(passed)[:TOP_N]" in main_text
        or "rank_screening_candidates(passed)[:TOP_N" in main_text
    )
    strategy_text=texts.get("src/strategy_builder.py","")
    strategy_research_only=(
        "research" in strategy_text.lower()
        and "production_eligible" in strategy_text
    )

    decision_path=base/"research_data/intraday_pit/decisions.csv"
    historical_decision_stream_present=(
        decision_path.exists() and decision_path.stat().st_size>0
    )

    blockers=[]
    if formal["status"]!="PASS":
        blockers.append(
            "FORMAL_FROZEN_V14_SOURCE_REGISTRY_BLOCKED:"
            + ",".join(formal.get("unresolved") or [])
        )
    if top100_truncation:
        blockers.append("CURRENT_SCANNER_CANDIDATE_POOL_TRUNCATED_TOP_N")
    if not historical_decision_stream_present:
        blockers.append("NO_HISTORICAL_CANONICAL_DECISION_STREAM")
    if strategy_research_only:
        blockers.append("RESEARCH_ONLY_STRATEGY_BUILDER_NOT_VALID_V14_SUBSTITUTE")

    return {
        "schema_version":"FROZEN_V14_REPLAY_READINESS_V1_2",
        "formal_source_registry":formal,
        "diagnostic_code_scan":{
            "production_source_files_scanned":len(production_files),
            "rule_mentions":rule_mentions,
            "rule_implementation_owners":rule_implementation_owners,
            "metadata_only_modules":sorted(METADATA_ONLY_MODULES),
            "core_rule_registry":registry_rules,
            "core_rule_registry_missing_w2_rules":registry_missing,
            "scanner_candidate_pool_truncated_by_top_n":top100_truncation,
            "strategy_builder_research_only":strategy_research_only,
        },
        "historical_decision_stream_present":historical_decision_stream_present,
        "status":"PASS" if not blockers else "FROZEN_ALPHA_INPUT_REQUIRED",
        "blockers":blockers,
        "governance":{
            "formal_registry_has_priority":True,
            "registry_metadata_counts_as_rule_implementation":False,
            "research_strategy_may_substitute_for_v14":False,
            "threshold_reconstruction_by_w3a":False,
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
