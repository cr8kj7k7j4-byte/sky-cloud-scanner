"""Conservative static inventory, NOT proof of provider request de-duplication."""
from __future__ import annotations

import json
from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")
SHARED_GROUP = "group: sky-fugle-paid-global-research-v1"


def audit(root: Path = WORKFLOW_DIR) -> dict:
    rows = []
    for path in sorted(root.glob("*.yml")) + sorted(root.glob("*.yaml")):
        source = path.read_text(encoding="utf-8")
        if "secrets.FUGLE_API_KEY" not in source:
            continue
        row = {
            "workflow": path.name,
            "references_paid_fugle_secret": True,
            "shared_group": SHARED_GROUP in source,
            "preflight_present": "python -m research.sky_paid_fugle_api_guard" in source,
            "receipt_readback": "sky_paid_fugle_api_guard --verify" in source,
        }
        row["candidate_guarded"] = all([
            row["shared_group"], row["preflight_present"], row["receipt_readback"],
        ])
        rows.append(row)
    uncovered = [r["workflow"] for r in rows if not r["candidate_guarded"]]
    return {
        "schema": "SKY_PAID_FUGLE_STATIC_ENTRYPOINT_AUDIT_V1",
        "secret_referencing_workflow_count": len(rows),
        "guard_candidate_count": sum(r["candidate_guarded"] for r in rows),
        "unguarded_candidate_count": len(uncovered),
        "unguarded_workflows": uncovered,
        "workflows": rows,
        "no_market_calls": True,
        "request_dedup_e2e_verified": False,
        "repository_wide_acceptance": "HOLD" if uncovered else "REQUIRES_RUNTIME_VERIFICATION",
        "note": "Static secret reference and structural guard check only; dynamic calls and dispatch must be separately audited.",
    }


def main():
    result = audit()
    out = Path("output/fugle_api_guard/static_inventory.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "workflows"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
