"""W6 five-minute read-only PR/CI monitor; never deploys, trades or repairs code."""
from __future__ import annotations
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PR_NUMBER = 365
ISSUE_NUMBER = 363
EXPECTED_CHECKS = 17
DEADLINE = datetime.fromisoformat("2026-11-09T10:38:00+08:00")
OUTPUT = Path("output/w6_risk_monitor/report.json")


def analyze(pr: dict, runs: list[dict], now: datetime) -> dict:
    """Only verifies CI for the current PR SHA, never the actual broker ledger."""
    now = now.astimezone(timezone.utc)
    sha = str(pr.get("head", {}).get("sha") or "")
    report = {
        "schema": "W6_PR_MONITOR_V1", "checked_at_utc": now.isoformat(),
        "head_sha": sha, "pr_number": PR_NUMBER,
        "source": "GitHub pull_request Actions, no broker data",
        "last_successful_run_id": None, "last_successful_run_url": None,
        "ci_success_count": 0, "ci_expected_count": EXPECTED_CHECKS,
        "ci_failure_ids": [], "ci_pending_ids": [], "status": "UNVERIFIED",
        "production_eligible": False, "trading_enabled": False,
        "broker_ledger_verified": False, "safe_automatic_repair_performed": False,
    }
    if now > DEADLINE.astimezone(timezone.utc):
        report["status"] = "MONITOR_WINDOW_ENDED"
        return report
    if pr.get("state") != "open" or pr.get("draft") is not True:
        report["status"] = "PR_STATE_CHANGED_REQUIRES_W0_REVIEW"
        return report
    if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        report["status"] = "PR_HEAD_UNKNOWN"
        return report
    relevant = [r for r in runs if r.get("head_sha") == sha and r.get("event") == "pull_request"]
    success = [r for r in relevant if r.get("status") == "completed" and r.get("conclusion") == "success"]
    failed = [r for r in relevant if r.get("status") == "completed"
              and r.get("conclusion") not in ("success", "skipped", "neutral")]
    pending = [r for r in relevant if r.get("status") != "completed"]
    report["ci_success_count"] = len(success)
    report["ci_failure_ids"] = sorted(int(r["id"]) for r in failed)
    report["ci_pending_ids"] = sorted(int(r["id"]) for r in pending)
    if success:
        best = max(success, key=lambda r: str(r.get("created_at", "")))
        report["last_successful_run_id"] = best.get("id")
        report["last_successful_run_url"] = best.get("html_url")
    if failed:
        report["status"] = "CI_FAILURE_W0_REVIEW"
    elif len(success) >= EXPECTED_CHECKS and not pending:
        report["status"] = "PR_CI_PASS_ONLY"
    else:
        report["status"] = "CI_PENDING_OR_INCOMPLETE"
    return report


def fingerprint(report: dict) -> str:
    data = {"status": report["status"], "head": report["head_sha"],
            "failures": report["ci_failure_ids"]}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:18]


def api(repo: str, path: str, token: str, *, method="GET", payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "sky-w6-risk-ci-read-only-monitor",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request("https://api.github.com/repos/" + repo + "/" + path,
                  data=body, headers=headers, method=method)
    with urlopen(req, timeout=20) as res:
        return json.load(res)


def maybe_alert(report: dict, repo: str, token: str) -> bool:
    """Idempotent W0 issue comment only for an identified failure/PR-state change."""
    if report["status"] not in ("CI_FAILURE_W0_REVIEW", "PR_HEAD_UNKNOWN",
                                "PR_STATE_CHANGED_REQUIRES_W0_REVIEW"):
        return False
    marker = "W6_MONITOR_INCIDENT:" + fingerprint(report)
    previous = api(repo, f"issues/{ISSUE_NUMBER}/comments?per_page=100", token)
    if any(marker in str(x.get("body", "")) for x in previous):
        return False
    body = (
        f"<!-- {marker} -->\n### W6 5-minute CI monitor: {report['status']}\n"
        f"PR https://github.com/{repo}/pull/{PR_NUMBER}; head `{report['head_sha']}`\n"
        f"Failed run IDs: {report['ci_failure_ids']}\n"
        f"Last successful check: {report['last_successful_run_url'] or 'none'}\n"
        "Requires W0 review. No code changes, secrets, deployment, trades or auto reruns.\n"
    )
    api(repo, f"issues/{ISSUE_NUMBER}/comments", token, method="POST", payload={"body": body})
    return True


def main() -> int:
    now = datetime.now(timezone.utc)
    over = now > DEADLINE.astimezone(timezone.utc)
    if over:
        report = analyze({}, [], now)
    else:
        token = os.getenv("GH_TOKEN")
        repo = os.getenv("GITHUB_REPOSITORY")
        if not token or not repo or "/" not in repo:
            raise RuntimeError("GITHUB_MONITOR_AUTH_MISSING")
        pr = api(repo, f"pulls/{PR_NUMBER}", token)
        head = str(pr.get("head", {}).get("sha") or "")
        query = urlencode({"event": "pull_request", "head_sha": head, "per_page": 100})
        runs = api(repo, "actions/runs?" + query, token).get("workflow_runs", [])
        report = analyze(pr, runs, now)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "head_sha": report["head_sha"],
                      "ci_success_count": report["ci_success_count"],
                      "ci_failure_ids": report["ci_failure_ids"],
                      "trading_enabled": False}, ensure_ascii=False))
    if over:
        return 0
    if report["status"] in ("CI_FAILURE_W0_REVIEW", "PR_HEAD_UNKNOWN",
                            "PR_STATE_CHANGED_REQUIRES_W0_REVIEW"):
        maybe_alert(report, repo, token)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (HTTPError, URLError, OSError, RuntimeError, ValueError) as exc:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps({
            "schema": "W6_PR_MONITOR_V1", "status": "MONITOR_ERROR",
            "error_type": type(exc).__name__, "trading_enabled": False,
            "production_eligible": False,
        }, indent=2) + "\n")
        print("MONITOR_ERROR:" + type(exc).__name__)
        sys.exit(2)
