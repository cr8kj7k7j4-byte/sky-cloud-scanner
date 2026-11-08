"""Fail-closed integration acceptance report, not a deployment or trade-authorizing tool.

Evidence is collected by separately authenticated workflows and Cloud Run.
This program NEVER synthesizes evidence, market quotes, model weights or orders.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

REQUIRED = (
    "market_universe", "paid_fugle", "six_model_inference",
    "private_ledger", "cloud_run", "risk_decision_loop"
)
EVIDENCE_KEYS = {
    "market_universe": ("market_date", "tse_count", "otc_count", "source", "scan_run_id"),
    "paid_fugle": ("request_at", "http_status", "source", "run_id"),
    "six_model_inference": ("model_results", "inference_run_id", "input_fingerprint"),
    "private_ledger": ("record_count", "readback_verified", "object_prefix", "run_id"),
    "cloud_run": ("service", "revision", "deployed_commit", "http_verified", "run_id"),
    "risk_decision_loop": ("risk_gate_executed", "decision_recorded", "order_sent", "run_id"),
}

def audit(evidence):
    if not isinstance(evidence, dict):
        raise ValueError("evidence_must_be_object")
    checks = {}
    for name in REQUIRED:
        row = evidence.get(name)
        problems = []
        if not isinstance(row, dict):
            problems.append("MISSING_VERIFIABLE_EVIDENCE")
            row = {}
        for key in EVIDENCE_KEYS[name]:
            if row.get(key) is None or row.get(key) == "":
                problems.append("MISSING_" + key.upper())
        if row.get("verified") is not True:
            problems.append("NOT_VERIFIED")
        if name == "market_universe":
            if not (isinstance(row.get("tse_count"), int) and row["tse_count"] > 0 and
                    isinstance(row.get("otc_count"), int) and row["otc_count"] > 0):
                problems.append("UNIVERSE_COVERAGE_UNVERIFIED")
        if name == "paid_fugle":
            if row.get("http_status") != 200 or row.get("source") != "FUGLE_PAID":
                problems.append("PAID_API_NOT_VERIFIED")
        if name == "six_model_inference":
            models = row.get("model_results")
            if not isinstance(models, list) or len(models) != 6:
                problems.append("REQUIRES_SIX_DISTINCT_MODELS")
            else:
                ids = [m.get("model_id") for m in models if isinstance(m, dict)]
                if len(ids) != 6 or len(set(ids)) != 6 or not all(ids):
                    problems.append("DUPLICATE_OR_INVALID_MODEL_ID")
                if any(not isinstance(m, dict) or m.get("executed") is not True or
                       m.get("real_inference") is not True or
                       not m.get("model_version") or not m.get("input_fingerprint")
                       for m in models):
                    problems.append("MODEL_INFERENCE_PROVENANCE_UNVERIFIED")
        if name == "private_ledger":
            if not isinstance(row.get("record_count"), int) or row["record_count"] < 6 or row.get("readback_verified") is not True:
                problems.append("IMMUTABLE_READBACK_OR_COVERAGE_UNVERIFIED")
        if name == "cloud_run":
            if row.get("http_verified") is not True or not row.get("revision"):
                problems.append("LIVE_REVISION_NOT_VERIFIED")
        if name == "risk_decision_loop":
            if row.get("risk_gate_executed") is not True or row.get("decision_recorded") is not True:
                problems.append("RISK_OR_DECISION_NOT_EXECUTED")
            if row.get("order_sent") is not False:
                problems.append("UNAUTHORIZED_ORDER_STATE")
        checks[name] = {"status": "PASS" if not problems else "PENDING",
                        "reasons": sorted(set(problems))}
    return {
        "schema": "sky-six-model-integrated-acceptance-v1",
        "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "overall": "ENGINEERING_ACCEPTED" if all(x["status"] == "PASS" for x in checks.values()) else "INSUFFICIENT_DATA",
        "production_promotion": False, "trading_authorized": False,
        "note": "Engineering acceptance never grants strategy profitability or P0-G promotion.",
        "checks": checks
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--evidence", default="output/six_model_verified_evidence.json")
    p.add_argument("--out", default="output/six_model_integration_acceptance.json")
    args = p.parse_args()
    source = Path(args.evidence)
    evidence = json.loads(source.read_text(encoding="utf-8")) if source.is_file() else {}
    result = audit(evidence)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"overall": result["overall"], "checks": result["checks"]}, ensure_ascii=False))
    return 0 if result["overall"] == "ENGINEERING_ACCEPTED" else 2

if __name__ == "__main__":
    raise SystemExit(main())
