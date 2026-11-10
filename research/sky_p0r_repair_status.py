"""Bounded read-only monitoring of P0-R PAPER_ONLY research repair and CI.

Runs under the existing five-minute recovery watchdog; does not alter
strategies, fabricate paper trades, touch brokers, merge PRs or promote Production.
Only a failed P0-R unit test workflow may be re-run ONCE after a transient
failure; no scanner, data collection or deployment is ever re-triggered.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = os.environ.get("GITHUB_REPOSITORY", "cr8kj7k7j4-byte/sky-cloud-scanner")
PR_NUMBER = 508
BRANCH = "research/p0r-failclosed-guards-20261110"
OUT = Path("output/sky_p0r_repair_monitor")
API = "https://api.github.com/repos/" + REPO
SAFE_RETRY_WORKFLOW = "P0-R Risk Engine Tests"


def request_json(path, method="GET", token=None, tries=2):
    token = token if token is not None else os.getenv("GH_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "sky-p0r-research-monitor"}
    if token:
        headers["Authorization"] = "Bearer " + token
    for attempt in range(tries):
        try:
            req = Request(API + path, headers=headers, method=method)
            with urlopen(req, timeout=12) as response:
                data = response.read()
            return json.loads(data) if data else {}
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            if attempt + 1 == tries:
                raise RuntimeError("GITHUB_API_UNAVAILABLE:" + type(exc).__name__) from exc
            time.sleep(1)
    raise RuntimeError("GITHUB_API_UNAVAILABLE")


def evaluate(pr, checks, paper_runs, artifacts=None, now=None):
    now = now or datetime.now(timezone.utc)
    head = (pr.get("head") or {}).get("sha")
    runs = paper_runs.get("workflow_runs") or []
    paper = next((r for r in runs if r.get("head_sha") == head), None)
    check_list = checks.get("check_runs") or []
    failed = [c for c in check_list if c.get("conclusion") in ("failure", "timed_out", "cancelled")]
    pending = [c for c in check_list if c.get("status") != "completed"]
    succeeded = sum(c.get("conclusion") == "success" for c in check_list)
    artifact_names = [x.get("name") for x in ((artifacts or {}).get("artifacts") or []) if not x.get("expired")]
    updated = pr.get("updated_at")
    hours_since_update = None
    if updated:
        try:
            hours_since_update = round((now - datetime.fromisoformat(updated.replace("Z", "+00:00"))).total_seconds() / 3600, 2)
        except (ValueError, TypeError):
            pass
    reasons = []
    if pr.get("state") != "open" and not pr.get("merged"):
        reasons.append("PR_NOT_OPEN")
    if pr.get("draft"):
        reasons.append("PR_AWAITING_REVIEW")
    if not head:
        reasons.append("PR_SHA_MISSING")
    if failed:
        reasons.append("CI_FAILURE")
    if pending:
        reasons.append("CI_IN_PROGRESS")
    if not check_list:
        reasons.append("CHECK_RUNS_NOT_AVAILABLE")
    if not paper or paper.get("status") != "completed" or paper.get("conclusion") != "success":
        reasons.append("PAPER_ACCEPTANCE_WORKFLOW_NOT_SUCCESSFUL_FOR_HEAD")
    if not any(str(n).startswith("sky-paper-only-acceptance-") for n in artifact_names):
        reasons.append("PAPER_ACCEPTANCE_ARTIFACT_NOT_VERIFIED")
    if hours_since_update is not None and hours_since_update > 6 and pr.get("draft"):
        reasons.append("NO_PR_UPDATE_OVER_6_HOURS")
    # Passing tests/artifact upload is NOT evidence that a simulated ledger exists.
    reasons.extend(["PAPER_LEDGER_RUNTIME_PROVENANCE_PENDING",
                    "PAPER_EXECUTION_COST_FILL_EVIDENCE_PENDING",
                    "SCAN_TO_P0R_INTEGRATION_PENDING",
                    "W0_P0G_APPROVAL_PENDING"])
    return {
        "schema": "SKY_P0R_REPAIR_MONITOR_V1",
        "checked_at_utc": now.isoformat(),
        "scheduled_interval_minutes": 5,
        "actual_schedule_cadence_guaranteed": False,
        "pr_number": PR_NUMBER,
        "pr_url": pr.get("html_url"),
        "pr_head_sha": head,
        "draft": bool(pr.get("draft")),
        "merged": bool(pr.get("merged")),
        "hours_since_pr_update": hours_since_update,
        "checks_total": len(check_list),
        "checks_success": succeeded,
        "checks_failed": len(failed),
        "checks_pending": len(pending),
        "paper_acceptance_run_url": paper.get("html_url") if paper else None,
        "paper_acceptance_artifacts": artifact_names,
        "code_checks_pass": bool(check_list and not failed and not pending),
        "paper_ledger_verified": False,
        "real_live_execution_enabled": False,
        "broker_account_required_for_research": False,
        "review_status": "HOLD" if reasons else "PENDING_W0",
        "blockers": sorted(set(reasons)),
        "automatic_code_rewrite": False,
        "automatic_production_promotion": False,
        "trade_action": "禁止交易",
    }


def safe_retry_candidate(runs, sha):
    """At most one re-run of a FAILED, fresh, PR P0-R unit-test run."""
    if not sha:
        return None
    now = datetime.now(timezone.utc)
    for run in runs.get("workflow_runs") or []:
        if not (run.get("name") == SAFE_RETRY_WORKFLOW
                and run.get("event") == "pull_request"
                and run.get("head_branch") == BRANCH
                and run.get("head_sha") == sha
                and run.get("status") == "completed"
                and run.get("conclusion") == "failure"
                and run.get("run_attempt") == 1):
            continue
        try:
            age = (now - datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))).total_seconds()
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= age <= 5400:
            return run["id"]
    return None


def schedule_cadence(schedule_runs, now=None):
    """Check actual schedule events, not just existence of a cron expression."""
    now = now or datetime.now(timezone.utc)
    records = schedule_runs.get("workflow_runs") or []
    scheduled = [r for r in records if r.get("event") == "schedule"]
    instants = []
    for row in scheduled:
        try:
            instant = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            if instant.tzinfo is not None and instant <= now:
                instants.append(instant)
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    instants.sort(reverse=True)
    if not instants:
        return {"status": "UNKNOWN_NO_SCHEDULE_EVIDENCE", "minutes_since_last_schedule": None,
                "last_schedule_utc": None, "last_interval_minutes": None}
    age = round((now - instants[0]).total_seconds() / 60, 2)
    gap = round((instants[0] - instants[1]).total_seconds() / 60, 2) if len(instants) >= 2 else None
    # GitHub schedule is best effort; this reports evidence, not a guarantee.
    status = "DELAYED_OVER_15_MINUTES" if age > 15 or (gap is not None and gap > 15) else (
        "INSUFFICIENT_INTERVAL_EVIDENCE" if gap is None else "RECENT_SCHEDULE_OBSERVED")
    return {"status": status, "minutes_since_last_schedule": age,
            "last_schedule_utc": instants[0].isoformat(), "last_interval_minutes": gap}


def collect(api=request_json):
    problems = []
    try:
        pr = api("/pulls/" + str(PR_NUMBER))
        sha = (pr.get("head") or {}).get("sha")
        checks = api("/commits/" + sha + "/check-runs?per_page=100") if sha else {}
        paper_runs = api("/actions/workflows/sky-paper-only-acceptance.yml/runs?per_page=15")
        matched = next((r for r in paper_runs.get("workflow_runs", []) if r.get("head_sha") == sha), None)
        artifacts = api("/actions/runs/" + str(matched["id"]) + "/artifacts") if matched else {}
        report = evaluate(pr, checks, paper_runs, artifacts)
        try:
            schedules = api("/actions/workflows/sky-recovery-watchdog.yml/runs?event=schedule&per_page=3")
            report["schedule_cadence"] = schedule_cadence(schedules)
        except RuntimeError as exc:
            report["schedule_cadence"] = schedule_cadence({})
            report["schedule_cadence"]["error"] = str(exc)
        if report["schedule_cadence"]["status"] != "RECENT_SCHEDULE_OBSERVED":
            report["blockers"].append("FIVE_MINUTE_SCHEDULE_CADENCE_NOT_VERIFIED")
        # A retry is permitted for one exact PR unit-test workflow; never auto-fix code.
        report["bounded_retry"] = "NONE"
        if os.getenv("SKY_P0R_RETRY_FAILED_TEST_ONCE") == "true" and report["checks_failed"] > 0:
            ci_runs = api("/actions/runs?event=pull_request&per_page=100")
            run_id = safe_retry_candidate(ci_runs, sha)
            if run_id is not None:
                try:
                    api("/actions/runs/" + str(run_id) + "/rerun-failed-jobs", method="POST")
                    report["bounded_retry"] = "RERAN_FAILED_P0R_UNIT_TESTS_ONCE"
                    report["retried_run_url"] = "https://github.com/" + REPO + "/actions/runs/" + str(run_id)
                except RuntimeError as exc:
                    problems.append(str(exc))
                    report["bounded_retry"] = "RETRY_FAILED_REVIEW_REQUIRED"
        if problems:
            report["monitor_errors"] = problems
        return report
    except RuntimeError as exc:
        return {"schema": "SKY_P0R_REPAIR_MONITOR_V1",
                "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                "monitor_status": "UNKNOWN_API_BLOCKED",
                "monitor_errors": [str(exc)],
                "production_eligible": False,
                "trade_action": "禁止交易",
                "broker_account_required_for_research": False}


def main():
    report = collect()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# P0-R repair health (PAPER_ONLY)", "",
             "Scheduled: every 5 minutes; GitHub may delay or skip actual runs.",
             "PR: https://github.com/" + REPO + "/pull/" + str(PR_NUMBER),
             "Checks success / fail / pending: " + str(report.get("checks_success", "?")) + " / " +
             str(report.get("checks_failed", "?")) + " / " + str(report.get("checks_pending", "?")),
             "Bounded retry: " + report.get("bounded_retry", "NONE"),
             "Actual scheduler cadence: " + str((report.get("schedule_cadence") or {}).get("status", "UNKNOWN")), "",
             "## Still requires verified evidence"]
    lines.extend("- " + x for x in report.get("blockers", report.get("monitor_errors", ["UNKNOWN"])))
    lines += ["", "No broker account needed for research; no real trades, no Production changes."]
    (OUT / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if report.get("monitor_status") == "UNKNOWN_API_BLOCKED":
        raise SystemExit("P0R_MONITOR_GITHUB_API_UNAVAILABLE")


if __name__ == "__main__":
    main()
