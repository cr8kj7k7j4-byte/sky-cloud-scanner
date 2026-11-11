"""Read-only W0 repair status monitor for the existing five-minute Actions watchdog.

No paid market calls, source code edits, auto-merge, trade orders, or retries of CI.
Retries below apply only to transient GitHub GET requests.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TARGET_PRS = (506, 508, 510, 511, 512)
OUTPUT = Path("output/sky_repair_progress")


def http_get_json(url, token, getter=None, sleep=None):
    getter = getter or urllib.request.urlopen
    sleep = sleep or time.sleep
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "sky-repair-progress-readonly",
    })
    for attempt in range(3):
        try:
            with getter(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        sleep(attempt + 1)
    raise RuntimeError("unreachable")


def summarize(pr, runs):
    head = (pr.get("head") or {}).get("sha")
    matching = [r for r in runs if r.get("head_sha") == head]
    passed = sum(r.get("conclusion") == "success" for r in matching)
    failed = sum(r.get("conclusion") in ("failure", "timed_out", "action_required") for r in matching)
    pending = sum(r.get("status") != "completed" for r in matching)
    cancelled = sum(r.get("conclusion") in ("cancelled", "skipped") for r in matching)
    if pr.get("merged") or pr.get("state") == "closed":
        state = "CLOSED_VERIFY_GOVERNANCE"
    elif failed:
        state = "CI_FAILED_NEEDS_ENGINEERING"
    elif pending:
        state = "CI_IN_PROGRESS"
    elif not matching:
        state = "NO_LATEST_HEAD_CI_EVIDENCE"
    elif pr.get("draft"):
        state = "CI_GREEN_DRAFT_REQUIRES_ACCEPTANCE"
    else:
        state = "CI_GREEN_REVIEW_REQUIRED"
    return {
        "number": pr.get("number"), "title": pr.get("title"), "url": pr.get("html_url"),
        "head_sha": head, "draft": pr.get("draft"), "state": pr.get("state"),
        "updated_at": pr.get("updated_at"), "status": state,
        "ci_runs_examined": len(matching), "ci_success": passed,
        "ci_failure": failed, "ci_pending": pending, "ci_cancelled": cancelled,
        "latest_head_only": True, "market_certification": "NOT_VERIFIED",
        "production_promotion": False,
    }


def collect(fetch, now=None):
    now = now or datetime.now(timezone.utc)
    details, errors = [], []
    for number in TARGET_PRS:
        try:
            pr = fetch("pulls/" + str(number))
            head = (pr.get("head") or {}).get("sha")
            if not isinstance(head, str) or len(head) != 40:
                raise ValueError("INVALID_HEAD_SHA")
            query = "actions/runs?event=pull_request&head_sha=" + urllib.parse.quote(head) + "&per_page=100"
            runs = fetch(query).get("workflow_runs", [])
            if not isinstance(runs, list):
                raise ValueError("INVALID_RUN_LIST")
            details.append(summarize(pr, runs))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                ValueError, TypeError, KeyError, AttributeError) as exc:
            errors.append({"pr": number, "reason": type(exc).__name__})
    failed = sum(x["ci_failure"] > 0 for x in details)
    waiting = sum(x["ci_pending"] > 0 for x in details)
    return {
        "schema": "SKY_W0_REPAIR_PROGRESS_V1",
        "checked_at_utc": now.astimezone(timezone.utc).isoformat(),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "watchdog_cadence": "5_MINUTES_BEST_EFFORT_GITHUB_ACTIONS",
        "mode": "READ_ONLY_NO_AUTONOMOUS_CODE_EDITS",
        "monitored_prs": list(TARGET_PRS),
        "details": details, "monitored_count": len(details),
        "ci_failed_pr_count": failed, "ci_active_pr_count": waiting,
        "fetch_errors": errors,
        "health": "BLOCKED_NEEDS_HUMAN_ENGINEERING" if errors or failed else
                  "CI_RUNNING" if waiting else "CI_FINISHED_ACCEPTANCE_PENDING",
        "remediation": (
            "Retry transient GitHub GET only (maximum two retries); "
            "failed CI requires log review and separately tested research PR. "
            "Never blindly rerun paid scans, stale quotes or governance jobs."
        ),
        "unverified_gates": [
            "Fugle per-symbol actual-execution timestamp and session freshness",
            "Real failed-run Artifact download/readback",
            "P0-R PAPER_ONLY input and cost evidence",
            "W0/P0-G documented human review",
        ],
        "production_eligible": False, "automatic_order": False,
        "auto_merge": False,
        "warning": "Green CI and an Actions success do not certify repair or live trading.",
    }


def write_report(report, output=OUTPUT):
    output.mkdir(parents=True, exist_ok=True)
    (output / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Sky W0 repair progress (read-only)", "",
        "Checked UTC: " + report["checked_at_utc"],
        "Health: " + report["health"],
        "No Production promotion, no autonomous edits, no orders.", "",
        "| PR | Status | CI pass | CI fail | CI pending |",
        "|---|---|---:|---:|---:|",
    ]
    for p in report["details"]:
        lines.append(f"| #{p['number']} | {p['status']} | {p['ci_success']} | {p['ci_failure']} | {p['ci_pending']} |")
    lines += ["", "## Unverified gates"] + ["- " + x for x in report["unverified_gates"]]
    if report["fetch_errors"]:
        lines += ["", "## GitHub read errors"] + [
            "- PR #{}: {}".format(e["pr"], e["reason"]) for e in report["fetch_errors"]
        ]
    (output / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    token, repo = os.getenv("GH_TOKEN"), os.getenv("GITHUB_REPOSITORY", "")
    if not token or not repo or "/" not in repo:
        raise SystemExit("GITHUB_READ_CONTEXT_MISSING")
    base = "https://api.github.com/repos/" + repo + "/"
    report = collect(lambda path: http_get_json(base + path, token))
    write_report(report)
    print(json.dumps({k: report[k] for k in (
        "health", "monitored_count", "ci_failed_pr_count",
        "ci_active_pr_count", "fetch_errors")}, ensure_ascii=False))
    if report["fetch_errors"]:
        raise SystemExit("W0_PROGRESS_GITHUB_READ_INCOMPLETE")


if __name__ == "__main__":
    main()
