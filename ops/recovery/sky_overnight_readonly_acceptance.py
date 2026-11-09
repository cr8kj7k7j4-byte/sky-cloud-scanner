"""Read-only overnight health evidence. No orders, no Production changes, no workflow retries."""
from __future__ import annotations
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

END = datetime.fromisoformat("2026-11-10T01:30:00+00:00")
START = datetime.fromisoformat("2026-11-09T06:00:00+00:00")
TARGETS = {
    "intraday_scan": "scan.yml",
    "unified_commands": "sky-unified-commands.yml",
    "paid_snapshot_dispatch": "sky-full-market-five-minute-dispatch.yml",
    "private_snapshot": "sky-full-market-private.yml",
    "swing_v11": "swing-v11-live-scan.yml",
}

def get_runs(repo, token, workflow):
    url = ("https://api.github.com/repos/" + repo
           + "/actions/workflows/" + workflow + "/runs?per_page=3")
    request = urllib.request.Request(
        url, headers={"Authorization": "Bearer " + token,
                      "Accept": "application/vnd.github+json",
                      "User-Agent": "sky-overnight-health-monitor"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response).get("workflow_runs", [])

def observe(now, fetch):
    report = {
        "schema": "SKY_OVERNIGHT_READONLY_ACCEPTANCE_V1",
        "checked_at_utc": now.isoformat(),
        "checked_at_tpe": now.astimezone(
            __import__("zoneinfo").ZoneInfo("Asia/Taipei")).isoformat(),
        "window_end_utc": END.isoformat(),
        "monitoring_active": START <= now < END,
        "checks": {}, "production_trading_approved": False,
        "mobile_end_to_end_verified": False,
        "notice": "Workflow status only; a successful run does not establish market coverage or mobile readiness.",
    }
    if not report["monitoring_active"]:
        report["status"] = "OUTSIDE_MONITOR_WINDOW"
        return report
    unhealthy = False
    for key, workflow in TARGETS.items():
        try:
            runs = fetch(workflow)
            row = runs[0] if runs else {}
            item = {
                "workflow": workflow,
                "run_id": row.get("id"),
                "event": row.get("event"),
                "status": row.get("status", "missing"),
                "conclusion": row.get("conclusion"),
                "created_at": row.get("created_at"),
                "url": row.get("html_url"),
            }
            if not row:
                item["finding"] = "NO_RUN"
                unhealthy = True
            elif row.get("status") == "completed" and row.get("conclusion") == "failure":
                item["finding"] = "WORKFLOW_FAILURE"
                unhealthy = True
            elif row.get("conclusion") == "success":
                item["finding"] = "WORKFLOW_COMPLETED_NOT_DATA_VERIFIED"
            else:
                item["finding"] = "RUN_NOT_YET_CONFIRMED"
                unhealthy = True
        except Exception as exc:
            item = {"workflow": workflow, "finding": "READ_ERROR",
                    "error_type": type(exc).__name__}
            unhealthy = True
        report["checks"][key] = item
    report["status"] = "WORKFLOW_FAILURES_DETECTED" if unhealthy else "WORKFLOWS_FINISHED_NOT_END_TO_END_VERIFIED"
    return report

def main():
    now = datetime.now(timezone.utc)
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    if not repo or not token:
        raise SystemExit("MISSING_GITHUB_CONTEXT")
    report = observe(now, lambda w: get_runs(repo, token, w))
    path = Path("output/overnight_acceptance/health_latest.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if report["status"] == "WORKFLOW_FAILURES_DETECTED":
        print("::warning::Sky overnight check found unresolved workflow failures. No automatic code or Production changes.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
