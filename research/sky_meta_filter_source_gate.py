"""Read-only Sky v1.4 candidate-source admission audit.

No supported W0/P0-G certified source is registered today. This module cannot
generate, score or admit a candidate by trusting labels supplied by a caller.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
from pathlib import Path

STRATEGY = "Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP"
REQUIRED = (
    "market_gate", "sector_rs_gate", "multi_timeframe_gate",
    "phase_gate", "setup_gate", "trigger_gate", "anti_chase_gate",
    "rr_gate", "opportunity_ranking_gate", "execution_adjustment_gate",
)


def candidate_source_inventory(source_registry, observed_artifact=None):
    """Audit upstream provenance and return zero admitted candidates.

    A future registry/provider contract requires separate W0 signoff. Never
    infer eligibility from P0-C first_gate, a scan rank, or a user boolean.
    """
    if not isinstance(source_registry, dict):
        raise ValueError("missing_frozen_source_registry")
    if source_registry.get("strategy_id") != STRATEGY:
        raise ValueError("unexpected_strategy_registry")
    statuses = {str(x.get("rule")):str(x.get("status"))
                for x in source_registry.get("rules", []) if isinstance(x, dict)}
    unresolved = [name for name in REQUIRED
                  if statuses.get(name) not in (
                      "FROZEN_CANONICAL_IMPLEMENTATION", "HISTORICAL_SNAPSHOT"
                  )]
    observed = observed_artifact if isinstance(observed_artifact, dict) else {}
    quotes = observed.get("deep") if isinstance(observed.get("deep"), list) else []
    # Even if an upstream document asserts 'eligible', currently there is no
    # certified W0 provider fingerprint, so it CANNOT be admitted here.
    return {
        "schema": "sky-meta-filter-source-readiness-v0.1",
        "strategy": STRATEGY,
        "rule_providers_unresolved": unresolved,
        "market_artifact_present":bool(observed_artifact),
        "observed_shortlist_count":len(quotes),
        "v14_historical_replay_status": (
            "BLOCKED_FROZEN_PROVIDERS_MISSING" if unresolved
            else "AWAITING_W0_CERTIFIED_DECISION_SOURCE"
        ),
        "forward_source_status":"AWAITING_W0_CERTIFIED_DECISION_SOURCE",
        "admitted_candidates":[],
        "admitted_count":0,
        "research_meta_scoring_enabled":False,
        "private_ledger_write_enabled":False,
        "production_eligible":False,
        "order_authorized":False,
        "reason":"P0-C first_gate and ranking/scan observations are not certified v1.4 alpha decisions."
    }


def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--registry",required=True)
    ap.add_argument("--scan")
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    source=json.loads(Path(args.registry).read_text(encoding="utf-8"))
    scan=json.loads(Path(args.scan).read_text(encoding="utf-8")) if args.scan else None
    report=candidate_source_inventory(source,scan)
    dest=Path(args.out)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["forward_source_status"],
                      "admitted":0,"production_eligible":False},ensure_ascii=False))


if __name__=="__main__":
    main()
