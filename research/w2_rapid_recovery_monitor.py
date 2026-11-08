"""W2 rapid 5-minute research monitor; no trading, cloud, or code writes.

Only GitHub public/authorized metadata is read. The sole permitted write
updates W2's dedicated issue #368 when a status transition occurs.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

REPO = "cr8kj7k7j4-byte/sky-cloud-scanner"
PR_NUMBER = 361
ISSUE_NUMBER = 368
# Last observed green W2 PR baseline: GitHub commit 21/21 PR CI success.
KNOWN_GREEN_BASELINE = "1974573462c6f89dfe5beb80220598bc6e5dbb60"
START = datetime(2026, 11, 8, 10, 38, tzinfo=ZoneInfo("Asia/Taipei"))
DEADLINE = datetime(2026, 11, 9, 10, 38, tzinfo=ZoneInfo("Asia/Taipei"))
REQUIRED_WORKFLOWS = (
    "W2 Private Research Ledger Read-only Audit",
    "Three Model Fugle Historical Private Ledger (Research Only)",
    "Three Model Next Session Markout (Research Only)",
    "Three Model Evidence Gate (Research Only)",
)
STATE_START = "<!-- W2_MONITOR_REPORT_BEGIN -->"
STATE_END = "<!-- W2_MONITOR_REPORT_END -->"


def utc_time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("untrusted_naive_timestamp")
    return result.astimezone(timezone.utc)


def assess(pr: dict, runs: list[dict], now: datetime) -> dict:
    """Classify head-specific PR CI without confusing it with paid/live E2E."""
    if now.utcoffset() is None:
        raise ValueError("monitor_requires_timezone")
    if not pr or pr.get("number") != PR_NUMBER:
        raise ValueError("unexpected_pr_identity")
    head = (pr.get("head") or {}).get("sha")
    if not re.fullmatch(r"[0-9a-f]{40}", str(head)):
        raise ValueError("invalid_head_sha")
    if pr.get("merged") is True:
        return {"status": "PR_MERGED_MONITOR_MAIN", "head_sha": head,
                "checks": {}, "failed_run_urls": [],
                "research_only": True, "production_approved": False}
    if pr.get("state") != "open":
        return {"status": "ACTION_REQUIRED_PR_CLOSED_UNMERGED", "head_sha": head,
                "checks": {}, "failed_run_urls": [],
                "research_only": True, "production_approved": False}
    now_utc = now.astimezone(timezone.utc)
    if now_utc < START.astimezone(timezone.utc):
        return {"status": "NOT_YET_STARTED", "head_sha": head, "checks": {},
                "failed_run_urls": [], "research_only": True,
                "production_approved": False}
    if now_utc > DEADLINE.astimezone(timezone.utc):
        return {"status": "MONITOR_WINDOW_CLOSED", "head_sha": head,
                "checks": {}, "failed_run_urls": [],
                "research_only": True, "production_approved": False}
    expected = {name: None for name in REQUIRED_WORKFLOWS}
    for run in runs:
        if (run.get("name") not in expected
                or run.get("event") != "pull_request"
                or run.get("head_sha") != head):
            continue
        name = run["name"]
        previous = expected[name]
        if previous is None or utc_time(run["created_at"]) > utc_time(previous["created_at"]):
            expected[name] = run
    checks = {}
    failed = []
    missing = False
    incomplete = False
    for name, run in expected.items():
        if run is None:
            checks[name] = "MISSING"
            missing = True
            continue
        if run.get("status") != "completed":
            checks[name] = "PENDING"
            incomplete = True
        elif run.get("conclusion") == "success":
            checks[name] = "SUCCESS"
        else:
            checks[name] = "FAILURE:" + str(run.get("conclusion"))
            failed.append(str(run.get("html_url") or
                              f"https://github.com/{REPO}/actions/runs/{run.get('id')}"))
    updated_at = utc_time(pr["updated_at"])
    grace = now_utc - updated_at < timedelta(minutes=30)
    if failed:
        status = "ACTION_REQUIRED_FAILED_CI"
    elif missing and not grace:
        status = "ACTION_REQUIRED_MISSING_CI"
    elif missing or incomplete:
        status = "CI_PENDING"
    else:
        status = "OFFLINE_CI_PASS_REAL_E2E_HOLD"
    return {
        "status": status, "head_sha": head, "checks": checks,
        "failed_run_urls": sorted(set(failed)),
        "research_only": True, "production_approved": False,
        "real_gcs_new_audit_verified": False,
        "first_nov9_schedule_verified": False,
        "trained_six_model_inference_verified": False,
    }


MAIN_WORKFLOW_EVENTS = {
    "schedule": (
        "Three Model Research Daily Dispatcher (No Cloud Credentials)",
        "Three Model Evening Schedule Health (Research Only)",
    ),
    "workflow_dispatch": (
        "Three Model Research Daily Dispatcher (No Cloud Credentials)",
        "Three Model Fugle Historical Private Ledger (Research Only)",
        "Three Model Next Session Markout (Research Only)",
    ),
}


def assess_main_research_runs(schedule_runs: list[dict],
                              dispatch_runs: list[dict],
                              now: datetime, head: str) -> dict:
    """Monitor live main runs after PR merges; do not infer paid data validity."""
    if now.utcoffset() is None:
        raise ValueError("monitor_requires_timezone")
    failed = []
    in_progress = []
    count = 0
    for event, runs in (("schedule", schedule_runs),
                        ("workflow_dispatch", dispatch_runs)):
        for run in runs:
            if (run.get("event") != event or run.get("head_branch") != "main"
                    or run.get("name") not in MAIN_WORKFLOW_EVENTS[event]):
                continue
            try:
                when = utc_time(run["created_at"])
            except (KeyError, ValueError, TypeError):
                continue
            if not START.astimezone(timezone.utc) <= when <= now.astimezone(timezone.utc):
                continue
            count += 1
            if run.get("status") != "completed":
                in_progress.append(str(run.get("id")))
            elif run.get("conclusion") != "success":
                failed.append(str(run.get("html_url") or
                                  f"https://github.com/{REPO}/actions/runs/{run.get('id')}"))
    if failed:
        status = "ACTION_REQUIRED_MAIN_RESEARCH_RUN_FAILURE"
    elif in_progress:
        status = "MAIN_RESEARCH_RUN_IN_PROGRESS"
    else:
        # A manual dispatch success never proves that a schedule event fired.
        status = "MAIN_RESEARCH_MONITORED_SCHEDULE_NOT_YET_VERIFIED"
    return {
        "status": status, "head_sha": head,
        "checks": {"main_research_runs_seen": count,
                   "main_research_in_progress": len(in_progress)},
        "failed_run_urls": sorted(set(failed)),
        "research_only": True, "production_approved": False,
        "real_gcs_new_audit_verified": False,
        "first_nov9_schedule_verified": False,
        "trained_six_model_inference_verified": False,
    }


def update_issue_body(existing: str, result: dict) -> tuple[str, bool]:
    """Idempotent state updates, preserves human-authored notes outside markers."""
    tracked = {k: result.get(k) for k in (
        "status", "head_sha", "last_confirmed_green_sha",
        "checks", "failed_run_urls", "research_only", "production_approved", "real_gcs_new_audit_verified",
        "first_nov9_schedule_verified", "trained_six_model_inference_verified")}
    payload = json.dumps(tracked, ensure_ascii=False, sort_keys=True, indent=2)
    signature = hashlib.sha256(payload.encode()).hexdigest()[:24]
    section = (f"{STATE_START}\n### 五分鐘研究監控最新狀態（僅 W2）\n"
               f"狀態：**{result['status']}**；PR head：`{result['head_sha']}`。\n"
               "程式 CI 成功不代表真實 Fugle/GCS、定時 schedule、策略驗證或正式下單資格。\n"
               f"\n```json\n{payload}\n```\n"
               f"<!-- W2_MONITOR_SIGNATURE:{signature} -->\n{STATE_END}")
    if f"<!-- W2_MONITOR_SIGNATURE:{signature} -->" in existing:
        return existing, False
    if STATE_START in existing and STATE_END in existing:
        start = existing.index(STATE_START)
        end = existing.index(STATE_END) + len(STATE_END)
        updated = existing[:start] + section + existing[end:]
    else:
        updated = existing.rstrip() + "\n\n" + section + "\n"
    return updated, True


def api(method: str, path: str, data: dict | None = None) -> dict:
    if method not in ("GET", "PATCH") or not path.startswith(f"/repos/{REPO}/"):
        raise ValueError("unsupported_github_api_request")
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("missing_monitor_token")
    payload = None if data is None else json.dumps(data).encode()
    req = Request("https://api.github.com" + path, data=payload, method=method,
                  headers={"Authorization": "Bearer " + token,
                           "Accept": "application/vnd.github+json",
                           "User-Agent": "sky-w2-research-monitor",
                           "X-GitHub-Api-Version": "2022-11-28",
                           "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=20) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"github_monitor_api_http_{exc.code}") from None


def main() -> None:
    now = datetime.now(timezone.utc)
    if now > DEADLINE.astimezone(timezone.utc):
        # Explicitly time-bounded; do not keep editing the issue indefinitely.
        print(json.dumps({"status": "MONITOR_WINDOW_CLOSED", "writes": 0}))
        return
    pr = api("GET", f"/repos/{REPO}/pulls/{PR_NUMBER}")
    sha = (pr.get("head") or {}).get("sha")
    if not re.fullmatch(r"[0-9a-f]{40}", str(sha)):
        raise ValueError("missing_pr_sha")
    # GitHub Actions REST supports head_sha and event to target this PR precisely.
    data = api("GET", f"/repos/{REPO}/actions/runs?event=pull_request"
               f"&head_sha={sha}&per_page=100")
    runs = data.get("workflow_runs", [])
    if not isinstance(runs, list):
        raise ValueError("missing_workflow_run_list")
    result = assess(pr, runs, now)
    if result["status"] == "PR_MERGED_MONITOR_MAIN":
        # After W0 merges this research-only PR, monitor real main workflow
        # metadata instead of stopping on PR state=closed.
        schedule = api("GET", f"/repos/{REPO}/actions/runs?event=schedule&per_page=100")
        dispatch = api("GET", f"/repos/{REPO}/actions/runs?event=workflow_dispatch&per_page=100")
        result = assess_main_research_runs(schedule.get("workflow_runs", []),
                                           dispatch.get("workflow_runs", []),
                                           now, sha)
    # Never present a failing new HEAD as the most recent verified good build.
    result["last_confirmed_green_sha"] = (
        sha if result["status"] == "OFFLINE_CI_PASS_REAL_E2E_HOLD"
        else KNOWN_GREEN_BASELINE
    )
    issue = api("GET", f"/repos/{REPO}/issues/{ISSUE_NUMBER}")
    if issue.get("number") != ISSUE_NUMBER or "pull_request" in issue:
        raise ValueError("incorrect_tracking_issue")
    new_body, changed = update_issue_body(issue.get("body") or "", result)
    if changed:
        api("PATCH", f"/repos/{REPO}/issues/{ISSUE_NUMBER}", {"body": new_body})
    print(json.dumps({"status": result["status"], "head_sha": result["head_sha"],
                      "checks": result["checks"], "issue_updated": changed,
                      "issue": f"https://github.com/{REPO}/issues/{ISSUE_NUMBER}",
                      "trading_enabled": False}, ensure_ascii=False))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
            summary.write(f"### W2 快速監控\n狀態：{result['status']}；Issue #{ISSUE_NUMBER}\n"
                          "研究-only，不自動修復程式、部署或下單。\n")
    if result["status"].startswith("ACTION_REQUIRED"):
        # GitHub job failure is an alarm even if the Issue PATCH worked.
        raise SystemExit(1)


if __name__ == "__main__":
    main()
