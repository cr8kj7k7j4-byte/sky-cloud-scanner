"""Read-only Sky workflow inventory and narrow fail-closed anti-duplication gate.

This is a static guard, NOT a live Actions-run, Fugle API or account-access audit.
Runs inside the already-required governance-e2e check; creates no schedules.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

CANONICAL_SCAN = "scan.yml"
SCAN_CRONS = ("5,15,30,50 1 * * 1-5", "15 2 * * 1-5")
PAID_RE = re.compile(r"FUGLE_API_KEY|api\.fugle\.tw", re.I)
CRON_RE = re.compile(r'^\s*- cron:\s*[\'"]?([^\'"#\n]+)', re.M)
# An active top-level `on.schedule` is recognized only when indented as YAML
# structure. Comments such as "# schedule:" do not activate schedules.


def workflow_info(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    on_block = []
    inside_on = False
    for line in lines:
        if re.match(r'^(?:"on"|\'on\'|on):\s*(?:#.*)?$', line):
            inside_on = True
            continue
        if inside_on:
            if line and not line[0].isspace() and not line.lstrip().startswith("#"):
                break
            on_block.append(line)
    active = False
    schedules = []
    for line in on_block:
        if re.match(r'^  schedule:\s*(?:#.*)?$', line):
            active = True
            continue
        if active:
            if re.match(r'^  [A-Za-z_][\w-]*:\s*', line):
                active = False
                continue
            m = CRON_RE.match(line)
            if m:
                schedules.append(m.group(1).strip())
    paid = bool(PAID_RE.search(content))
    return {
        "file": path.name,
        "active_schedule": bool(schedules),
        "cron_utc": schedules,
        "has_workflow_dispatch": bool(re.search(r"(?m)^  workflow_dispatch:", content)),
        "paid_endpoint_reference": paid,
        "atomic_enforce_reference": "SKY_PAID_ATOMIC_ENFORCE" in content,
        "concurrency_group": (re.search(r"(?m)^  group:\s*(.+)", content) or [None, None])[1],
        "runs_main_scanner": bool(re.search(r"python\s+-m\s+src\.main(?:\s|$)", content)),
    }



def reuse_first_fallback_contract(repo_root: Path) -> dict:
    """Static REUSE_FIRST/FALLBACK_PROVIDER_FIRST safety inventory only.

    A passing static check never certifies live Fugle permission, claim
    concurrency, executed-trade freshness, PIT or Production eligibility.
    Reuse existing canonical implementation; do not introduce a controller.
    """
    required_sources = {
        "registry": "SKY_SYSTEM_REGISTRY_V2_1.md",
        "canonical_scan": ".github/workflows/scan.yml",
        "plan_a_acceptance": "research/sky_intraday_plan_a_two_track_acceptance.py",
        "five_minute_probe": "src/sky_v14_ticker_candles_probe.py",
        "trades_vwap_reviewer": "research/sky_stage5_vwap_cost_evidence.py",
        "paid_claim_guard": "research/sky_paid_fugle_api_guard.py",
        "research_freeze": "research/RESEARCH_FREEZE_REGISTRY.md",
        "validation_protocol": "docs/SKY_VALIDATION_PROTOCOL_V1_0.md",
    }
    texts = {}
    failures = []
    for name, relpath in required_sources.items():
        try:
            texts[name] = (repo_root / relpath).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            failures.append("MISSING_CANONICAL_SOURCE:" + relpath)
            texts[name] = ""

    checks = {
        "governance_policy": all(
            token in texts["registry"]
            for token in ("SKY_W0_REUSE_FIRST_FALLBACK_V1", "REUSE_FIRST",
                          "FALLBACK_PROVIDER_FIRST", "EVIDENCE_BEFORE_PASS",
                          "REJECT_DUPLICATE", "NO_TRADE")
        ),
        "single_paid_claim_before_scanner": all(
            step in texts["canonical_scan"] for step in (
                "Reserve shared paid Fugle slot before any paid observations",
                "Independently verify paid reservation",
                "steps.verify_claim.outcome == 'success'",
                "SKY_PAID_ATOMIC_ENFORCE: '1'",
            )
        ),
        "two_track_plan_a_and_source_inventory": all(
            step in texts["canonical_scan"] for step in (
                "Record separate Plan A A1 snapshot and A2 candidate acceptance",
                "Preserve same-run raw-source availability manifest",
                "Verify operational market coverage",
            )
        ),
        "five_minute_provider_semantics_fail_closed": all(
            step in texts["five_minute_probe"] for step in (
                '"bar_timestamp_semantics_certified":False',
                '"bar_volume_cross_source_reconciled":False',
                '"avg_price_is_certified_vwap":False',
            )
        ),
        "tick_vwap_source_not_self_certified": all(
            step in texts["trades_vwap_reviewer"] for step in (
                '"source_provenance_certified": False',
                '"quote_cutoff_pit_certified": False',
                '"vwap_certified": False',
                '"production_eligible": False',
            )
        ),
    }
    scanner = texts["canonical_scan"].split("      - name: Run scanner", 1)
    scanner_body = scanner[1].split(
        "      - name: Publish all MCR research observations", 1
    )[0] if len(scanner) == 2 else ""
    checks["canonical_scan_execution_cost_gate"] = (
        scanner_body.count('EXEC_ENFORCE_GATE: "1"') == 1
        and 'SKY_FUGLE_ONLY_MARKETDATA: "1"' in scanner_body
    )
    failures.extend("REUSE_FIRST_CONTRACT_DRIFT:" + name
                    for name, passed in checks.items() if not passed)
    return {
        "schema": "SKY_W0_REUSE_FIRST_FALLBACK_STATIC_CONTRACT_V1",
        "scope": "STATIC_RESEARCH_GOVERNANCE_NOT_LIVE_SOURCE_CERTIFICATION",
        "checked_sources": required_sources,
        "checks": checks,
        "failures": failures,
        "live_fugle_entitlement_verified": False,
        "same_run_live_data_verified": False,
        "production_eligible": False,
    }


def audit(root: Path) -> dict:
    workflows = sorted(root.glob("*.yml")) + sorted(root.glob("*.yaml"))
    records = [workflow_info(p) for p in workflows]
    by_name = {r["file"]: r for r in records}
    failures = []
    canonical = by_name.get(CANONICAL_SCAN)
    if canonical is None:
        failures.append("CANONICAL_SCAN_WORKFLOW_MISSING")
    elif canonical["active_schedule"]:
        # W0 #363: the user retired all formal timed intraday scans.
        # Any reintroduced cron must fail governance; manual dispatch remains valid.
        failures.append("RETIRED_CANONICAL_SCAN_SCHEDULE_REACTIVATED")
    for r in records:
        if r["file"] != CANONICAL_SCAN:
            if set(r["cron_utc"]) & set(SCAN_CRONS):
                failures.append("DUPLICATE_CANONICAL_SCAN_CRON:" + r["file"])
            if r["active_schedule"] and r["runs_main_scanner"]:
                failures.append("DUPLICATE_SCHEDULED_MAIN_SCANNER:" + r["file"])
        if r["file"] == "sky-full-market-five-minute-dispatch.yml" and r["active_schedule"]:
            failures.append("PAID_FIVE_MIN_DISPATCH_REACTIVATED")
    cron_owners = defaultdict(list)
    for r in records:
        for cron in r["cron_utc"]:
            cron_owners[cron].append(r["file"])
    # Same cron can legitimately schedule different jobs. Report overlap for
    # owner review, never auto-delete jobs on temporal overlap alone.
    shared_crons = [
        {"cron_utc": cron, "workflows": sorted(owners)}
        for cron, owners in sorted(cron_owners.items())
        if len(owners) > 1
    ]
    return {
        "schema": "SKY_W0_WORKFLOW_DEDUP_AUDIT_V1",
        "workflows_inspected": len(records),
        "scheduled_workflows": sum(r["active_schedule"] for r in records),
        "paid_reference_workflows": sum(r["paid_endpoint_reference"] for r in records),
        "shared_crons_review_only": shared_crons,
        "potential_unprotected_paid_workflows_review_only": [
            r["file"] for r in records
            if r["paid_endpoint_reference"] and not r["atomic_enforce_reference"]
        ],
        "checks": {
            "single_canonical_daytrade_schedule": not any(
                x.startswith(("CANONICAL", "DUPLICATE_CANONICAL", "DUPLICATE_SCHEDULED")) for x in failures
            ),
            "five_minute_paid_dispatch_remains_unscheduled": (
                "PAID_FIVE_MIN_DISPATCH_REACTIVATED" not in failures
            ),
        },
        "failures": failures,
        "workflows": records,
    }


def main() -> int:
    root = Path(".github/workflows")
    result = audit(root)
    reuse_contract = reuse_first_fallback_contract(Path("."))
    result["reuse_first_fallback_static_contract"] = reuse_contract
    result["failures"].extend(reuse_contract["failures"])
    output = Path("output/w0_workflow_dedup_audit.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "workflows_inspected": result["workflows_inspected"],
        "scheduled_workflows": result["scheduled_workflows"],
        "shared_cron_groups_need_review": len(result["shared_crons_review_only"]),
        "paid_workflows_need_owner_review": result["potential_unprotected_paid_workflows_review_only"],
        "reuse_first_contract_checks": reuse_contract["checks"],
        "failures": result["failures"],
        "audit_file": str(output),
    }, ensure_ascii=False))
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
