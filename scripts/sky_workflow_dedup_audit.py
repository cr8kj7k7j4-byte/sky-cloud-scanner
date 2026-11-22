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


def audit(root: Path) -> dict:
    workflows = sorted(root.glob("*.yml")) + sorted(root.glob("*.yaml"))
    records = [workflow_info(p) for p in workflows]
    by_name = {r["file"]: r for r in records}
    failures = []
    canonical = by_name.get(CANONICAL_SCAN)
    if canonical is None:
        failures.append("CANONICAL_SCAN_WORKFLOW_MISSING")
    elif tuple(canonical["cron_utc"]) != SCAN_CRONS:
        failures.append("CANONICAL_FIVE_SCAN_SCHEDULE_DRIFT")
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
    output = Path("output/w0_workflow_dedup_audit.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "workflows_inspected": result["workflows_inspected"],
        "scheduled_workflows": result["scheduled_workflows"],
        "shared_cron_groups_need_review": len(result["shared_crons_review_only"]),
        "paid_workflows_need_owner_review": result["potential_unprotected_paid_workflows_review_only"],
        "failures": result["failures"],
        "audit_file": str(output),
    }, ensure_ascii=False))
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
