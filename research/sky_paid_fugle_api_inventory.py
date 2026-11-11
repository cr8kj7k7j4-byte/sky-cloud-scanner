"""Read-only Fugle-paid Workflow inventory; never imply inactive == safe.

Classify syntax rather than guessing activity. A secret reference is not proof
of a billable API call; manual/push triggers can still execute when cron is absent.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")
SHARED_GROUP = "group: sky-fugle-paid-global-research-v1"
CONFIG_ONLY_EXEMPTIONS = {"three-model-cloud-auth-preflight.yml"}

# Evidence is intentionally narrower than complete runtime enforcement.
# These paths have an explicit research opt-in, scoped GitHub token and a
# source-level request guard. A caller may still use an unreviewed path.
ATOMIC_WIRED_SOURCE_CANDIDATES = {
    "sky-chat-bridge.yml": "src/fugle.py",
    "sky-fugle-stage2-probe.yml": "src/sky_fugle_stage2_probe.py",
    "fugle-2026-entitlement-probe.yml": "research/fugle_2026_entitlement_probe.py",
}


def atomic_wired_candidate(workflow: str, source: str, *, repository_root: Path) -> bool:
    path = ATOMIC_WIRED_SOURCE_CANDIDATES.get(workflow)
    if not path:
        return False
    if not all(mark in source for mark in (
        "SKY_PAID_ATOMIC_ENFORCE: '1'",
        "GH_TOKEN: ${{ github.token }}",
        "contents: write",
    )):
        return False
    target = repository_root / path
    if not target.is_file():
        return False
    return "guard_fugle_request(" in target.read_text(encoding="utf-8")



def triggers(source: str) -> dict:
    # Only uncommented lines with a top-level on: nested YAML indentation.
    lines = source.splitlines()
    in_on = False
    flags = {"schedule": False, "workflow_dispatch": False,
             "push": False, "pull_request": False, "workflow_run": False}
    for line in lines:
        if line == "on:":
            in_on = True
            continue
        if in_on and line and not line[0].isspace() and not line.lstrip().startswith("#"):
            break
        if in_on and line.startswith("  ") and not line.startswith("    "):
            matched = re.match(r"^  (schedule|workflow_dispatch|push|pull_request|workflow_run):", line)
            if matched:
                flags[matched.group(1)] = True
    return flags


def cohort(path: str) -> str:
    name = path.lower()
    if any(part in name for part in ("history", "backtest", "export", "opening-acceleration", "ml-pilot", "p0s-oos", "taiex-benchmark")):
        return "HISTORICAL_DATA_OR_BACKTEST"
    if any(part in name for part in ("preflight", "cloud-auth")):
        return "PREFLIGHT_REQUIRES_CALL_PATH_REVIEW"
    if any(part in name for part in ("live-scan", "realtime", "quote", "scan", "market", "candidate", "unified")):
        return "LIVE_MARKET_OR_SCAN"
    return "RESEARCH_OR_PROVIDER_PROBE"


def audit(root: Path = WORKFLOW_DIR) -> dict:
    rows = []
    for path in sorted(root.glob("*.yml")) + sorted(root.glob("*.yaml")):
        source = path.read_text(encoding="utf-8")
        if not re.search(r"^\s*FUGLE_API_KEY:\s*\$\{\{\s*secrets\.FUGLE_API_KEY\s*\}\}", source, re.M):
            continue
        flags = triggers(source)
        row = {
            "workflow": path.name,
            "references_paid_fugle_secret": True,
            "shared_group": (SHARED_GROUP in source or
                             ("group: ${{" in source and
                              "sky-fugle-paid-global-research-v1" in source and
                              "github.event_name == 'pull_request'" in source)),
            "preflight_present": "python -m research.sky_paid_fugle_api_guard" in source,
            "receipt_readback": bool(re.search(r"sky_paid_fugle_api_guard[^\n]*--verify", source)),
            "triggers": flags,
            "static_cohort": cohort(path.name),
            "manual_or_event_trigger_available": any(flags.values()),
            "live_run_observed": None,
            "actual_paid_api_invocations": None,
            "owner_review_required": True,
            "configuration_only_exemption": path.name in CONFIG_ONLY_EXEMPTIONS,
            "atomic_endpoint_code_wired_candidate": atomic_wired_candidate(
                path.name, source, repository_root=Path(__file__).resolve().parents[1]),
            "central_reservation_job": "  sky_paid_reservation:" in source,
            "paid_job_dependencies": source.count("needs: sky_paid_reservation") + source.count(", sky_paid_reservation]"),
            "central_fail_closed_final_gate": "Fail job when claim is rejected or not verified" in source,
            # An Artifact reservation is NOT atomic across GitHub Runs.
            # The separate atomic-ref research proof is not a deployed paid gate.
            "atomic_endpoint_claim_enforced": (
                "sky_fugle_atomic_ref_claim" in source
                and "canonical_fugle_request" in source
                and "ATOMIC_CLAIM_VERIFIED_BEFORE_PAID" in source
            ),
        }
        row["candidate_guarded"] = all([
            row["shared_group"], row["preflight_present"], row["receipt_readback"],
            (not row["central_reservation_job"] or
             (row["central_fail_closed_final_gate"] and row["paid_job_dependencies"] > 0)),
        ])
        rows.append(row)
    uncovered = [r["workflow"] for r in rows
                 if not r["candidate_guarded"] and not r["configuration_only_exemption"]]
    exempt = [r["workflow"] for r in rows if r["configuration_only_exemption"]]
    return {
        "schema": "SKY_PAID_FUGLE_STATIC_ENTRYPOINT_AUDIT_V2",
        "secret_referencing_workflow_count": len(rows),
        "guard_candidate_count": sum(r["candidate_guarded"] for r in rows),
        "unguarded_candidate_count": len(uncovered),
        "unguarded_workflows": uncovered,
        "verified_configuration_only_exemptions": exempt,
        "exemption_count": len(exempt),
        "unguarded_schedule_enabled_count": sum(r["triggers"]["schedule"] for r in rows if not r["candidate_guarded"]),
        "unguarded_manual_or_event_count": sum(r["manual_or_event_trigger_available"] for r in rows if not r["candidate_guarded"]),
        "cohort_counts": {k: sum(r["static_cohort"] == k for r in rows) for k in sorted({r["static_cohort"] for r in rows})},
        "workflows": rows,
        "atomic_endpoint_code_wired_candidate_count": sum(
            r["atomic_endpoint_code_wired_candidate"] for r in rows),
        "atomic_endpoint_enforced_workflow_count": sum(r["atomic_endpoint_claim_enforced"] for r in rows),
        "atomic_endpoint_acceptance": "REQUIRES_RUNTIME_VERIFICATION",
        "no_market_calls": True,
        "request_dedup_e2e_verified": False,
        "repository_wide_acceptance": (
            "HOLD" if uncovered or any(
                not r["atomic_endpoint_claim_enforced"]
                for r in rows if not r["configuration_only_exemption"]
            ) else "REQUIRES_RUNTIME_VERIFICATION"
        ),
        "note": "Static source inspection only; zero uncovered does NOT prove endpoint-level cross-workflow de-duplication. Runtime and post-merge E2E remain mandatory.",
    }


def main():
    result = audit()
    out = Path("output/fugle_api_guard/static_inventory.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "workflows"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
