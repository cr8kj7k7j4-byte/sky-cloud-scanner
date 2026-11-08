"""Cross-check existing W4/P0-L official summary with Sky Meta forward gate.

Only uses the actual main-branch status snapshot; does not fetch market prices,
classify trades, invent missing v1.4 decisions or promote observations.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

BLOCK = "PRODUCTION_DECISION_PROVENANCE_BLOCKED"


def audit_w4_source_status(status, *, observed_at):
    if not isinstance(status, dict) or not isinstance(status.get("w4_dashboard"), dict):
        raise ValueError("W4_status_snapshot_required")
    if observed_at.tzinfo is None:
        raise ValueError("observed_at_requires_timezone")
    raw_time = status.get("generated_at_utc")
    if not isinstance(raw_time, str):
        raise ValueError("snapshot_time_missing")
    created = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
    if created.tzinfo is None:
        raise ValueError("snapshot_time_timezone_required")
    age_hours = (observed_at.astimezone(timezone.utc)-created.astimezone(timezone.utc)).total_seconds()/3600
    if age_hours < 0:
        raise ValueError("future_snapshot")
    dashboard = status["w4_dashboard"]
    forward = dashboard.get("forward_trade_provenance")
    evidence = dashboard.get("strategy_evidence_integrity")
    if not isinstance(forward, dict) or not isinstance(evidence, dict):
        raise ValueError("missing_strategy_provenance_evidence")
    verified = forward.get("authoritative_forward_rule_source_verified")
    trade_count = evidence.get("eligible_strategy_records")
    if verified is not False and verified is not True:
        raise ValueError("unverified_forward_rule_source_status")
    if type(trade_count) is not int or trade_count < 0:
        raise ValueError("invalid_strategy_evidence_count")
    # A proof-of-history dashboard could be old. It cannot authorize a
    # currently deployed forward source, even if it claims all rows qualified.
    return {
        "schema":"sky-meta-filter-existing-w4-provenance-v0.1",
        "generated_at_utc":created.isoformat(),
        "age_hours":round(age_hours,3),
        "snapshot_is_current_24h":age_hours <= 24,
        "ranking_observations":evidence.get("ranking_rows_loaded"),
        "strategy_eligible_records_reported":trade_count,
        "w0_source_claim_verified_in_snapshot":verified,
        "original_provenance_status":forward.get("status"),
        "w0_owner_issue":227,
        "research_meta_candidate_admission":0,
        "forward_scoring_enabled":False,
        "production_eligible":False,
        "order_authorized":False,
        "conclusion":"BLOCKED_W0_CERTIFIED_FORWARD_SOURCE_REQUIRED",
        "why":"W4 ranking and P0-L SHADOW_OBSERVATION record_id are not signed v1.4 decision_id; historical dashboard cannot certify new forward source."
    }


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--status",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    report=audit_w4_source_status(
        json.loads(Path(args.status).read_text(encoding="utf-8")),
        observed_at=datetime.now(timezone.utc)
    )
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"conclusion":report["conclusion"],
                      "snapshot_age_hours":report["age_hours"],
                      "meta_candidate_admission":0},ensure_ascii=False))


if __name__=="__main__":
    main()
