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

METADATA_ONLY_MODULES={"src/model_registry.py"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8",errors="ignore") if path.exists() else ""


def _rule_implementation_candidates(text: str, rule: str) -> bool:
    # A bare registry/list occurrence is not an executable rule provider.
    patterns=[
        rf'["\']{re.escape(rule)}["\']\s*:',
        rf'\b{re.escape(rule)}\s*=',
        rf'def\s+{re.escape(rule)}\s*\(',
        rf'def\s+\w*{re.escape(rule)}\w*\s*\(',
    ]
    return any(re.search(p,text) for p in patterns)


def audit_repo(root: str=".") -> dict:
    base=Path(root)
    src=base/"src"
    production_files=sorted(src.glob("*.py")) if src.exists() else []
    texts={str(p.relative_to(base)):_read(p) for p in production_files}

    rule_mentions={}
    rule_implementation_owners={}
    for rule in CANONICAL_RULE_COLUMNS:
        mentions=[path for path,text in texts.items() if rule in text]
        owners=[
            path for path,text in texts.items()
            if path not in METADATA_ONLY_MODULES
            and _rule_implementation_candidates(text,rule)
        ]
        rule_mentions[rule]=mentions
        rule_implementation_owners[rule]=owners

    all_rule_outputs_implemented=all(
        bool(rule_implementation_owners[x]) for x in CANONICAL_RULE_COLUMNS
    )

    model_registry=texts.get("src/model_registry.py","")
    m=re.search(r"CORE_RULE_IDS\s*=\s*\((.*?)\)",model_registry,flags=re.S)
    registry_rules=[]
    if m:
        registry_rules=re.findall(r'["\']([^"\']+)["\']',m.group(1))
    registry_missing=[x for x in CANONICAL_RULE_COLUMNS if x not in registry_rules]

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

    executable_v14_candidates=[
        path for path,text in texts.items()
        if path not in METADATA_ONLY_MODULES
        and ("v1.4" in text or "v14" in text.lower())
        and sum(
            _rule_implementation_candidates(text,rule)
            for rule in CANONICAL_RULE_COLUMNS
        )>=3
    ]

    decision_path=base/"research_data/intraday_pit/decisions.csv"
    historical_decision_stream_present=decision_path.exists() and decision_path.stat().st_size>0

    blockers=[]
    missing_impl=[k for k,v in rule_implementation_owners.items() if not v]
    if missing_impl:
        blockers.append("FROZEN_V14_RULE_OUTPUT_PROVIDER_MISSING:"+",".join(missing_impl))
    if registry_missing:
        blockers.append("W2_RULES_MISSING_FROM_CORE_RULE_REGISTRY:"+",".join(registry_missing))
    if not executable_v14_candidates:
        blockers.append("NO_EXECUTABLE_FROZEN_V14_REPLAY_ADAPTER")
    if top100_truncation:
        blockers.append("CURRENT_SCANNER_CANDIDATE_POOL_TRUNCATED_TOP_N")
    if not historical_decision_stream_present:
        blockers.append("NO_HISTORICAL_CANONICAL_DECISION_STREAM")
    if strategy_research_only:
        blockers.append("RESEARCH_ONLY_STRATEGY_BUILDER_NOT_VALID_V14_SUBSTITUTE")

    return {
        "schema_version":"FROZEN_V14_REPLAY_READINESS_V1_1",
        "production_source_files_scanned":len(production_files),
        "canonical_rule_columns":CANONICAL_RULE_COLUMNS,
        "rule_mentions":rule_mentions,
        "rule_implementation_owners":rule_implementation_owners,
        "metadata_only_modules":sorted(METADATA_ONLY_MODULES),
        "core_rule_registry":registry_rules,
        "core_rule_registry_missing_w2_rules":registry_missing,
        "all_rule_outputs_implemented_in_src":all_rule_outputs_implemented,
        "executable_v14_replay_candidates":executable_v14_candidates,
        "historical_decision_stream_present":historical_decision_stream_present,
        "scanner_snapshot":{
            "top100_field_present":'"top100"' in main_text,
            "deep_field_present":'"deep"' in main_text,
            "candidate_pool_truncated_by_top_n":top100_truncation,
        },
        "strategy_builder_research_only":strategy_research_only,
        "status":"PASS" if not blockers else "FROZEN_ALPHA_INPUT_REQUIRED",
        "blockers":blockers,
        "governance":{
            "registry_metadata_counts_as_rule_implementation":False,
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
