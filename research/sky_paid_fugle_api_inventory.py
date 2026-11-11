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
        if "secrets.FUGLE_API_KEY" not in source:
            continue
        flags = triggers(source)
        row = {
            "workflow": path.name,
            "references_paid_fugle_secret": True,
            "shared_group": SHARED_GROUP in source,
            "preflight_present": "python -m research.sky_paid_fugle_api_guard" in source,
            "receipt_readback": bool(re.search(r"sky_paid_fugle_api_guard[^\\n]*--verify", source)),
            "triggers": flags,
            "static_cohort": cohort(path.name),
            "manual_or_event_trigger_available": any(flags.values()),
            "live_run_observed": None,
            "actual_paid_api_invocations": None,
            "owner_review_required": True,
        }
        row["candidate_guarded"] = all([
            row["shared_group"], row["preflight_present"], row["receipt_readback"],
        ])
        rows.append(row)
    uncovered = [r["workflow"] for r in rows if not r["candidate_guarded"]]
    return {
        "schema": "SKY_PAID_FUGLE_STATIC_ENTRYPOINT_AUDIT_V2",
        "secret_referencing_workflow_count": len(rows),
        "guard_candidate_count": sum(r["candidate_guarded"] for r in rows),
        "unguarded_candidate_count": len(uncovered),
        "unguarded_workflows": uncovered,
        "unguarded_schedule_enabled_count": sum(r["triggers"]["schedule"] for r in rows if not r["candidate_guarded"]),
        "unguarded_manual_or_event_count": sum(r["manual_or_event_trigger_available"] for r in rows if not r["candidate_guarded"]),
        "cohort_counts": {k: sum(r["static_cohort"] == k for r in rows) for k in sorted({r["static_cohort"] for r in rows})},
        "workflows": rows,
        "no_market_calls": True,
        "request_dedup_e2e_verified": False,
        "repository_wide_acceptance": "HOLD" if uncovered else "REQUIRES_RUNTIME_VERIFICATION",
        "note": "Filename grouping is triage only. Inspect every paid call path, authorization, and runtime; zero cron does not mean inactive.",
    }


def main():
    result = audit()
    out = Path("output/fugle_api_guard/static_inventory.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "workflows"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
