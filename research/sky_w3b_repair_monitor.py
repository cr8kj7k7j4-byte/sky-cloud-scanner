"""Bounded five-minute PR #512 CI recovery evidence, never trading activation.

Runs as a companion job of the pre-existing sky-recovery-watchdog schedule.
Only reruns failed *unit-test* jobs once. Never merges a PR, edits source,
triggers paid market APIs, deploys, or changes governance / Production gates.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

PR_NUMBER = 512
UNIT_WORKFLOW = "sky-chat-bridge-tests.yml"
OUTPUT = Path("output/sky_recovery_watchdog/w3b_repair_monitor.json")
MAX_ATTEMPT = 1  # only the initial failed attempt may be retried
STALE_MINUTES = 45


def decide(pr, runs, now):
    """Pure decision function; never mistake passing CI for market readiness."""
    state = {"pr": PR_NUMBER, "checked_at_utc": now.isoformat(),
             "production_eligible": False, "live_trade": False,
             "real_market_5m_certified": False, "vwap_certified": False,
             "w0_p0g_approved": False, "action": "observe",
             "reason": "UNKNOWN", "run_id": None, "run_url": None}
    if not pr or not pr.get("head", {}).get("sha"):
        state.update(reason="MISSING_PR_EVIDENCE", action="blocked")
        return state
    state["head_sha"] = pr["head"]["sha"]
    state["pr_state"] = pr.get("state")
    state["draft"] = pr.get("draft")
    state["merged"] = pr.get("merged") is True
    if state["merged"]:
        state.update(reason="PR_MERGED_NEEDS_INDEPENDENT_MARKET_REVIEW",
                     action="review_required")
        return state
    if pr.get("state") != "open":
        state.update(reason="PR_CLOSED_UNMERGED", action="blocked")
        return state
    applicable = [r for r in runs if r.get("head_sha") == state["head_sha"]
                  and r.get("event") == "pull_request"
                  and r.get("path", "").endswith("/" + UNIT_WORKFLOW)]
    if not applicable:
        state.update(reason="NO_CURRENT_HEAD_UNIT_CI", action="blocked")
        return state
    run = max(applicable, key=lambda r: r.get("id") if isinstance(r.get("id"), int) else -1)
    state["run_id"] = run.get("id")
    state["run_url"] = run.get("html_url")
    state["run_status"] = run.get("status")
    state["run_conclusion"] = run.get("conclusion")
    if run.get("status") != "completed":
        state.update(reason="UNIT_CI_RUNNING", action="observe")
        return state
    if run.get("conclusion") == "success":
        state.update(reason="UNIT_CI_PASS_MARKET_REVIEW_PENDING",
                     action="review_required")
        return state
    if run.get("conclusion") not in ("failure", "timed_out"):
        state.update(reason="UNIT_CI_NOT_RETRYABLE", action="blocked")
        return state
    attempt = run.get("run_attempt")
    try:
        created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError, TypeError):
        state.update(reason="MISSING_CI_TIME", action="blocked")
        return state
    if (isinstance(attempt, bool) or not isinstance(attempt, int)
            or attempt != MAX_ATTEMPT
            or created.tzinfo is None
            or created > now + timedelta(minutes=2)
            or now - created > timedelta(minutes=STALE_MINUTES)):
        state.update(reason="RETRY_NOT_SAFE_OR_ALREADY_ATTEMPTED",
                     action="blocked")
        return state
    if not isinstance(run.get("id"), int) or isinstance(run["id"], bool):
        state.update(reason="INVALID_RUN_ID", action="blocked")
        return state
    state.update(reason="FRESH_FAILED_UNIT_CI_ONLY", action="retry_candidate")
    return state


def api(method, url, token):
    req = urllib.request.Request(
        url, method=method,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "sky-w3b-recovery-monitor"})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read()
        return json.loads(raw) if raw else {}


def monitor():
    token = os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo or "/" not in repo:
        raise RuntimeError("MISSING_GITHUB_CONTEXT")
    root = "https://api.github.com/repos/" + repo
    now = datetime.now(timezone.utc)
    pr = api("GET", root + "/pulls/" + str(PR_NUMBER), token)
    runs = api("GET", root + "/actions/runs?branch=" +
               "research%2Fw3b-five-minute-pit-rebase-20261110&per_page=100",
               token).get("workflow_runs", [])
    report = decide(pr, runs, now)
    report["check_mode"] = "SCHEDULED_REPAIR_EVIDENCE_ONLY"
    report["github_run_id"] = os.environ.get("GITHUB_RUN_ID")
    report["retries_authorized"] = (os.environ.get("SKY_W3B_SAFE_CI_RETRY", "false") == "true")
    if report["action"] == "retry_candidate" and report["retries_authorized"]:
        try:
            api("POST", root + "/actions/runs/" + str(report["run_id"]) +
                "/rerun-failed-jobs", token)
            report["action"] = "safe_unit_ci_retry_requested"
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            report.update(action="blocked", reason="CI_RETRY_API_ERROR",
                          error_type=type(exc).__name__)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if report["action"] == "blocked":
        raise RuntimeError(report["reason"])


if __name__ == "__main__":
    monitor()
