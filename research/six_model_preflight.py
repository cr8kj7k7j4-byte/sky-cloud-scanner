"""Read-only, fail-closed evidence preflight for the requested six-model study.

This does not execute a historical backtest, fetch private credentials or promote a model.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

START = "2026-01-01"
END = "2026-11-07"
EXPECTED = 6
REQUIRED = (
    "SKY_SYSTEM_REGISTRY_V2_1.md",
    "research/RESEARCH_FREEZE_REGISTRY.md",
    "docs/SKY_VALIDATION_PROTOCOL_V1_0.md",
)
PROOF_FIELDS = (
    "model_id", "version_sha", "executable_entrypoint",
    "frozen_rule_source", "data_source", "signal_ledger",
    "historical_results", "cost_stress_results",
)


def table_rows(text: str, heading: str) -> list[str]:
    section = text.split(heading, 1)
    if len(section) < 2:
        return []
    body = section[1].split("\n## ", 1)[0]
    return [x for x in body.splitlines()
            if x.startswith("|") and not re.match(r"^\|[ :|-]+\|$", x)
            and not x.startswith("| Type |") and not x.startswith("| Candidate |")]


def inventory(registry: str) -> dict:
    prod = table_rows(registry, "## Production baselines")
    candidates = table_rows(registry, "## Active research candidates")
    def parse(lines):
        values = []
        for line in lines:
            cells = [x.strip() for x in line.strip("|").split("|")]
            if len(cells) >= 3 and cells[0] not in ("Type", "Candidate"):
                values.append({"label": cells[1] if cells[0] == "Production" else cells[0],
                               "registry_status": cells[2] if cells[0] == "Production" else cells[1]})
        return values
    return {"production_baselines": parse(prod), "research_candidates": parse(candidates)}


def audit(root: Path, model_manifest: Path | None = None) -> dict:
    missing = [p for p in REQUIRED if not (root / p).is_file()]
    registry = (root / REQUIRED[0]).read_text(encoding="utf-8") if not missing or (root / REQUIRED[0]).exists() else ""
    observed = inventory(registry) if registry else {"production_baselines": [], "research_candidates": []}
    proofs = []
    manifest_status = "MISSING"
    if model_manifest and model_manifest.is_file():
        payload = json.loads(model_manifest.read_text(encoding="utf-8"))
        raw = payload.get("models", [])
        if not isinstance(raw, list):
            raise ValueError("manifest.models must be a list")
        manifest_status = "READ"
        seen = set()
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError("each model must be an object")
            missing_fields = [k for k in PROOF_FIELDS if not item.get(k)]
            model_id = item.get("model_id")
            if model_id in seen:
                missing_fields.append("unique_model_id")
            seen.add(model_id)
            proofs.append({"model_id": model_id, "verified": not missing_fields,
                           "missing_evidence": missing_fields})
    # Historical v1.4 full-rule reconstruction is explicitly forbidden without frozen provenance.
    limitation = root / "docs/W0_V14_HISTORICAL_REPLAY_GOVERNANCE_DECISION_20261026.md"
    historical_v14_blocked = (not limitation.is_file() or
                              "NOT FULLY RECONSTRUCTABLE" in limitation.read_text(encoding="utf-8"))
    all_six = (len(proofs) == EXPECTED and all(x["verified"] for x in proofs))
    blockers = []
    if missing:
        blockers.append("GOVERNANCE_FILES_MISSING")
    if not all_six:
        blockers.append("SIX_MODEL_INDEPENDENT_PROVENANCE_UNVERIFIED")
    if historical_v14_blocked:
        blockers.append("V14_HISTORICAL_FULL_RULE_REPLAY_UNAVAILABLE")
    blockers.append("FUGLE_AUTHENTICATED_2026_HISTORY_NOT_ATTESTED")
    blockers.append("SIX_INDEPENDENT_COSTED_BACKTESTS_NOT_ATTESTED")
    return {
        "schema": "SKY_SIX_MODEL_REPLAY_PREFLIGHT_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_period": {"start": START, "end": END,
                             "end_is_non_trading_day": date.fromisoformat(END).weekday() >= 5},
        "expected_distinct_models": EXPECTED,
        "manifest_status": manifest_status,
        "manifest_model_count": len(proofs),
        "manifest_proofs": proofs,
        "registry_discovery_only_not_six_model_mapping": observed,
        "missing_governance_files": missing,
        "blocking_reasons": blockers,
        "status": "INSUFFICIENT_DATA",
        "historic_backtest_executed": False,
        "fugle_api_called": False,
        "six_model_signal_activation": False,
        "production_changed": False,
        "next_action": "Map six actual deployed model IDs and attach independently verifiable provenance, then run governed history extraction and replay."
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--out", type=Path, default=Path("research_output/six_model_preflight.json"))
    args = parser.parse_args()
    result = audit(args.root, args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"],
                      "blockers": result["blocking_reasons"],
                      "output": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
