"""Read-only forward candidate-source readiness for Meta-Filter V0.1.

Do not treat a scanner job's success, market quote or research shortlist
as an authenticated Sky v1.4 strategy decision. Never auto-admit candidates.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from research.sky_meta_filter_source_gate import (
    candidate_source_inventory, REQUIRED, STRATEGY
)

# Structural fields required from a future W0-signed canonical decision stream.
REQUIRED_DECISION_FIELDS = (
    "decision_id", "strategy_id", "strategy_version", "source_run_id",
    "source_commit_sha", "candidate_at", "feature_cutoff_at", "symbol",
    "source_quote_at", "source_quote_provider", "candidate_pool_id",
    "canonical_rule_outputs", "p0r_status", "entry_trigger",
    "original_stop", "baseline_action",
)
UNSAFE_SUBSTITUTES = (
    "P0-C first_gate", "scan.deep", "rank_score",
    "research-only strategy_builder", "RF/XGB/NN proxy"
)


def build_forward_preflight(*, registry, scan_workflow_text, scan_artifact=None):
    if not isinstance(scan_workflow_text, str) or not scan_workflow_text:
        raise ValueError("scanner_workflow_required")
    source = candidate_source_inventory(registry, scan_artifact)
    # The workflow name is an operational runner, not proof of v1.4 alpha.
    job_name = re.search(r"^name:\s*(.+)$", scan_workflow_text, re.M)
    if not job_name:
        raise ValueError("scanner_workflow_name_missing")
    runner_name = job_name.group(1).strip()
    market_gate = "PASS_FULL_MARKET_LIVE" in scan_workflow_text
    has_schedule = "schedule:" in scan_workflow_text
    has_fugle = "FUGLE_API_KEY" in scan_workflow_text
    # One must not infer rule provenance from those three basic checks.
    artifact = scan_artifact if isinstance(scan_artifact, dict) else {}
    candidate_rows = artifact.get("deep")
    if not isinstance(candidate_rows, list):
        candidate_rows = []
    present = set()
    if candidate_rows:
        present = set.intersection(*[
            set(x.keys()) for x in candidate_rows if isinstance(x, dict)
        ]) if all(isinstance(x, dict) for x in candidate_rows) else set()
    missing = [x for x in REQUIRED_DECISION_FIELDS if x not in present]
    complete_provenance = (
        bool(candidate_rows)
        and not missing
        and not source["rule_providers_unresolved"]
        and source["forward_source_status"] == "CERTIFIED"
    )
    # Independently audited source cannot be established from a caller-asserted
    # field in a scan document; status is never CERTIFIED by this code.
    assert complete_provenance is False
    return {
        "schema":"sky-meta-filter-forward-source-preflight-v0.1",
        "scanner_workflow_name":runner_name,
        "scanner_schedule_declared":has_schedule,
        "fugle_secret_reference_present":has_fugle,
        "full_market_gate_declared":market_gate,
        "historical_rule_providers_unresolved":source["rule_providers_unresolved"],
        "sample_shortlist_rows":len(candidate_rows),
        "missing_decision_fields_in_sample":missing,
        "required_decision_fields":list(REQUIRED_DECISION_FIELDS),
        "unacceptable_substitutes":list(UNSAFE_SUBSTITUTES),
        "candidate_stream_status":"BLOCKED_PENDING_W0_P0G_SOURCE_CERTIFICATION",
        "admitted_candidates":0,
        "meta_model_scoring_enabled":False,
        "forward_private_ledger_enabled":False,
        "production_change":False,
        "order_authorized":False,
        "next_owner":"W0/P0-G",
        "next_evidence":"W0-signed canonical v1.4 source ID, frozen decision schema, feature-cutoff timestamps, actual future decision run + readback",
    }


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--registry", required=True)
    parser.add_argument("--scan-workflow", required=True)
    parser.add_argument("--scan")
    parser.add_argument("--out", required=True)
    opts=parser.parse_args()
    registry=json.loads(Path(opts.registry).read_text(encoding="utf-8"))
    workflow=Path(opts.scan_workflow).read_text(encoding="utf-8")
    sample=json.loads(Path(opts.scan).read_text(encoding="utf-8")) if opts.scan else None
    result=build_forward_preflight(registry=registry,scan_workflow_text=workflow,scan_artifact=sample)
    path=Path(opts.out)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["candidate_stream_status"],
                      "missing_fields":len(result["missing_decision_fields_in_sample"]),
                      "production_change":False},ensure_ascii=False))


if __name__=="__main__":
    main()
