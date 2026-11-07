"""Non-trading model evidence triage for GitHub issue #331.

A code file, an algorithm factory, or a registry candidate is NOT proof that
an independently deployed trading model exists or has valid after-cost edge.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REGISTRY = "SKY_SYSTEM_REGISTRY_V2_1.md"
FREEZE = "research/RESEARCH_FREEZE_REGISTRY.md"
PROTOCOL = "docs/SKY_VALIDATION_PROTOCOL_V1_0.md"
FUGLE_PROBE = "docs/SKY_FUGLE_2026_HISTORY_PROBE_LATEST.json"
PRODUCTION = (
    ("Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP", "FORWARD_ONLY", "HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE"),
    ("Sky Swing V1.0", "BLOCKED", "AUTHORITATIVE_MODEL_VERSION_AND_REPLAY_NOT_CONFIRMED"),
)
ML_FACTORIES = ("RANDOM_FOREST", "XGBOOST", "LIGHTGBM")
RESEARCH = (
    ("Swing 5D 3-factor top-decile challenger", "HOLD", "PIT_SURVIVORSHIP_COST_PORTFOLIO_BLOCKED"),
    ("Revenue MoM 5D", "BLOCKED", "MOPS_HISTORICAL_FILING_PIT_UNVERIFIED"),
    ("Revenue YoY 5D", "HOLD", "CONCENTRATION_GATE_FAILED"),
    ("Revenue YoY Acceleration 5D", "BLOCKED", "MOPS_HISTORICAL_FILING_PIT_UNVERIFIED"),
    ("Revenue YoY 20D", "HOLD", "CONCENTRATION_GATE_FAILED"),
)


def available_file(root: Path, rel: str) -> bool:
    return (root / rel).is_file()


def build_report(root: Path) -> dict:
    missing = [x for x in (REGISTRY, FREEZE, PROTOCOL) if not available_file(root,x)]
    registry = (root / REGISTRY).read_text(encoding="utf-8") if available_file(root, REGISTRY) else ""
    freeze = (root / FREEZE).read_text(encoding="utf-8") if available_file(root, FREEZE) else ""
    pairs = []
    for name,route,reason in PRODUCTION:
        match = name in registry
        pairs.append({"name":name,"category":"GOVERNED_PRODUCTION_BASELINE","registry_present":match,
                      "research_route":route if match else "BLOCKED",
                      "blocking_reason":reason if match else "REGISTRY_PROVENANCE_MISSING",
                      "six_deployed_ai_mapping_confirmed":False,
                      "production_authorization_changed":False})
    for name,route,reason in RESEARCH:
        match = name in registry
        frozen = name in freeze and "ARCHIVED_NO_RETUNE" in freeze
        pairs.append({"name":name,"category":"REGISTERED_RESEARCH_CANDIDATE","registry_present":match,
                      "research_route":"BLOCKED" if frozen or not match else route,
                      "blocking_reason":"ARCHIVED_RESEARCH_NO_RETUNE" if frozen else reason if match else "REGISTRY_PROVENANCE_MISSING",
                      "six_deployed_ai_mapping_confirmed":False,
                      "production_authorization_changed":False})
    src = (root/"src/model_training.py").read_text(encoding="utf-8") if available_file(root,"src/model_training.py") else ""
    algorithms = [{"algorithm":name,"factory_definition_present":('factories["'+name+'"]') in src,
                   "trained_weight_verified":False,"deployed_decision_model_verified":False}
                  for name in ML_FACTORIES]
    probe_status = "MISSING"
    evidence = {}
    probe_file = root/FUGLE_PROBE
    if probe_file.is_file():
        try:
            obj = json.loads(probe_file.read_text(encoding="utf-8"))
            evidence = {"generated_at_utc":obj.get("generated_at_utc"),
                        "sample_symbols": [x.get("symbol") for x in obj.get("results",[])],
                        "sample_api_data_returned": bool(obj.get("all_symbols_retrieved")),
                        "full_market_verified":False,
                        "full_period_verified":False}
            probe_status = "TWO_SYMBOL_API_OBSERVATION_ONLY" if evidence["sample_api_data_returned"] else "INCOMPLETE"
        except (ValueError,KeyError,TypeError):
            probe_status = "INVALID"
    return {
        "schema":"SKY_SIX_MODEL_EVIDENCE_TRIAGE_V1",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "scope":{"start":"2026-01-01","end":"2026-11-07","requested_models":6},
        "source_of_truth":"GitHub current checkout; registry statuses only, no live market quote",
        "governance_missing":missing,
        "governed_items_not_six_model_identification":pairs,
        "ml_algorithm_factories_not_deployed_models":algorithms,
        "fugle": {"status":probe_status,**evidence},
        "six_model_ids_independently_verified":0,
        "six_model_mapping_status":"BLOCKED_UNVERIFIED",
        "history_replay_status":"INSUFFICIENT_DATA",
        "next_blocker":"PIN_ACTUAL_SIX_DEPLOYED_MODEL_IDS_SOURCE_VERSION_RULES_WEIGHTS_AND_DECISION_ENTRYPOINTS",
        "five_minute_market_data_entitlement_fully_verified":False,
        "historical_model_backtests_executed":False,
        "forward_evidence_generated_by_this_job":False,
        "positive_after_cost_expectancy_certified":False,
        "production_changed":False,
        "automatic_orders":False,
        "next_actions":[
            "Locate authoritative mobile six-model config and deployed model IDs with exact versions.",
            "Verify per-model executable rule/weight provenance; isolate legacy v1.4 as forward only.",
            "Run PIT-valid, costed 0.45%/0.65% replay only for individually eligible models.",
            "Keep existing shadow outcome and W0/P0-G governance gates independent."
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root",default=".")
    ap.add_argument("--out",default="research_output/six_model_evidence_triage.json")
    args=ap.parse_args()
    result=build_report(Path(args.root))
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["six_model_mapping_status"],
                      "known_production_baselines":sum(x["category"]=="GOVERNED_PRODUCTION_BASELINE" for x in result["governed_items_not_six_model_identification"]),
                      "ml_algorithms":len(result["ml_algorithm_factories_not_deployed_models"]),
                      "out":str(out)},ensure_ascii=False))


if __name__=="__main__":
    main()
