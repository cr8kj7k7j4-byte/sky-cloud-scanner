"""Fail-closed evidence audit for three independent AI research models.

Usage: python -m research.three_model_evidence_gate --manifest research_output/three_models/manifest.json
This tool never trains, deploys or authorizes orders.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

MODELS = ("bidirectional_intraday", "next_day", "swing_3_20d")
REQUIRED_GATES = (
    "point_in_time", "leakage", "survivorship", "independent_oos",
    "walk_forward", "regime", "primary_cost", "stress_cost",
    "portfolio", "concentration", "liquidity", "drawdown",
    "shadow_paper", "p0_r", "p0_g",
)

def audit(manifest: dict, root: Path) -> dict:
    entries = manifest.get("models", {})
    results = {}
    for name in MODELS:
        row = entries.get(name, {})
        missing = []
        if row.get("model_id") != name:
            missing.append("model_id")
        for field in ("training_start", "training_end", "data_source",
                      "source_fingerprint", "feature_schema_version",
                      "train_samples", "validation_samples", "oos_samples",
                      "training_code_commit", "artifact_path", "artifact_sha256",
                      "validation_report_path", "validation_report_sha256"):
            if not row.get(field):
                missing.append(field)
        for field in ("train_samples", "validation_samples", "oos_samples"):
            if not isinstance(row.get(field), int) or row[field] <= 0:
                missing.append(field + "_positive")
        for path_key, hash_key in (
            ("artifact_path", "artifact_sha256"),
            ("validation_report_path", "validation_report_sha256"),
        ):
            p = row.get(path_key, "")
            if not isinstance(p, str) or not p:
                continue
            full = (root / p).resolve()
            if not full.is_relative_to(root.resolve()):
                missing.append(path_key + "_outside_root")
            elif not full.is_file():
                missing.append(path_key + "_missing")
            elif hashlib.sha256(full.read_bytes()).hexdigest() != row.get(hash_key):
                missing.append(hash_key + "_mismatch")
        if row.get("training_end") and row.get("training_start"):
            if str(row["training_end"]) < str(row["training_start"]):
                missing.append("date_order")
        gates = row.get("gates") if isinstance(row.get("gates"), dict) else {}
        missing += ["gate_" + g for g in REQUIRED_GATES if gates.get(g) != "PASS"]
        results[name] = {
            "evidence_complete": not missing,
            "missing_or_failed": sorted(set(missing)),
            "display_status": "EVIDENCE_COMPLETE_REVIEW_ONLY" if not missing else "UNTRAINED_OR_UNVERIFIED",
            "production_signal": False,
        }
    return {
        "schema": "sky-three-model-evidence-v1",
        "all_evidence_complete": all(x["evidence_complete"] for x in results.values()),
        "production_signal": False,
        "models": results,
        "note": "Evidence completeness is not a profit guarantee or deployment authorization.",
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", default="research_output/three_models/evidence_gate.json")
    args = ap.parse_args()
    path = Path(args.manifest)
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    result = audit(data, Path("."))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if not result["all_evidence_complete"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
