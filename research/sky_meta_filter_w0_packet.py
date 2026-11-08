"""Generate a W0/P0-G verification packet from actual source files.

A review packet is never an approval or candidate-admission artifact. It can
be regenerated when scanner and rule-source metadata change.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from research.sky_meta_filter_forward_preflight import (
    REQUIRED_DECISION_FIELDS, build_forward_preflight
)
from research.sky_meta_filter_source_gate import REQUIRED

DECISION_GROUPS = {
    "W0/P0-G": (
        "Approve canonical forward producer and release identity; no proxy substitution",
        "Verify signer/owner identity independently from a caller-provided JSON value",
        "Freeze Meta feature/time/score contract before evaluating unseen sessions",
    ),
    "W2": (
        "Produce deterministic existing v1.4 decision schema and ten Alpha rule outputs",
        "Prove signal emitted before entry, not reconstructed from price outcome",
    ),
    "W3A": (
        "Verify per-symbol Fugle quotation timestamp and point-in-time coverage",
        "Verify completed 5m candle semantics and cross-market source lineage",
    ),
    "W3B": (
        "Create privately scoped append-only durable observation and followup storage",
        "Prove object-create preconditions and byte-for-byte readback",
    ),
    "W6": (
        "Verify executable entry/stop/exit assumptions, spread and slippage",
        "Separate research proxy markout from actual execution and net PnL",
    ),
}


def build_packet(*, registry, workflow_text, workflow_sha, registry_sha):
    if not isinstance(workflow_sha,str) or len(workflow_sha)!=64:
        raise ValueError("workflow_sha256_required")
    if not isinstance(registry_sha,str) or len(registry_sha)!=64:
        raise ValueError("registry_sha256_required")
    preflight=build_forward_preflight(registry=registry,scan_workflow_text=workflow_text)
    statuses={rule["rule"]:rule.get("status","UNKNOWN")
              for rule in registry.get("rules",[]) if isinstance(rule,dict) and "rule" in rule}
    unresolved=[rule for rule in REQUIRED
                if statuses.get(rule) not in (
                    "FROZEN_CANONICAL_IMPLEMENTATION","HISTORICAL_SNAPSHOT")]
    return {
        "schema":"sky-meta-filter-w0-source-attestation-request-v0.1",
        "purpose":"W0/P0-G_REVIEW_ONLY_NOT_CERTIFICATION",
        "scan_workflow_sha256":workflow_sha,
        "source_registry_sha256":registry_sha,
        "strategy":registry["strategy_id"],
        "provider_matrix":[{"rule":rule,"status":statuses.get(rule,"MISSING")}
                           for rule in REQUIRED],
        "historical_unresolved_provider_count":len(unresolved),
        "scanner_contract":preflight,
        "required_forward_decision_fields":list(REQUIRED_DECISION_FIELDS),
        "approval_packet":None,
        "approved_provider_commit":None,
        "approved_decision_stream_uri":None,
        "trusted_signer_check":"NOT_IMPLEMENTED_NO_EXTERNAL_APPROVAL_SOURCE",
        "forward_observed_decision_run_id":None,
        "forward_readback_sha256":None,
        "owners":{k:list(v) for k,v in DECISION_GROUPS.items()},
        "release_status":"BLOCKED_AWAITING_INDEPENDENT_W0_P0G_CERTIFICATION",
        "admitted_candidates":0,
        "model_probabilities_available":False,
        "private_ledger_connected":False,
        "production_strategy_modified":False,
        "order_authorized":False,
    }


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--registry",required=True)
    p.add_argument("--workflow",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    registry_raw=Path(args.registry).read_bytes()
    workflow_raw=Path(args.workflow).read_bytes()
    report=build_packet(
        registry=json.loads(registry_raw),
        workflow_text=workflow_raw.decode("utf-8"),
        workflow_sha=sha256(workflow_raw).hexdigest(),
        registry_sha=sha256(registry_raw).hexdigest(),
    )
    destination=Path(args.out)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
                           encoding="utf-8")
    print(json.dumps({"schema":report["schema"],"unresolved":report["historical_unresolved_provider_count"],
                      "release_status":report["release_status"],"admitted_candidates":0},
                     ensure_ascii=False))


if __name__=="__main__":
    main()
