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
from zoneinfo import ZoneInfo
from pathlib import Path

TARGET_PRS = (508, 511, 512, 531, 536)
NEXT_ACTIONS = {
    508: ("OFF_MARKET", "WIRE_PAPER_LEDGER_EVENT_SOURCE_AND_VALIDATE_COSTS"),
    511: ("MARKET_SESSION", "CERTIFY_TWSE_TPEX_EXECUTED_TIMESTAMPS"),
    512: ("MARKET_SESSION", "VERIFY_CANDLE_CAUSALITY_AND_INTEGRATION"),
    531: ("OFF_MARKET", "WIRE_REAL_BRIDGE_ARTIFACT_READBACK"),
    536: ("OFF_MARKET", "VERIFY_CROSS_WORKFLOW_API_RESERVATION"),
}

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
    window, next_action = NEXT_ACTIONS.get(pr.get("number"), ("OFF_MARKET", "REVIEW_BLOCKER"))
    return {
        "work_window": window, "next_action": next_action,
        "repair_performed": False, "end_to_end_accepted": False,
        "number": pr.get("number"), "title": pr.get("title"), "url": pr.get("html_url"),
        "head_sha": head, "draft": pr.get("draft"), "state": pr.get("state"),
        "updated_at": pr.get("updated_at"), "status": state,
        "ci_runs_examined": len(matching), "ci_success": passed,
        "ci_failure": failed, "ci_pending": pending, "ci_cancelled": cancelled,
        "latest_head_only": True, "market_certification": "NOT_VERIFIED",
        "production_promotion": False,
    }



def route_work_items(details, now, user_blockers=None):
    """Independent fail-closed work routing. This prepares work, never executes it.

    user_blockers map PR numbers to operator action dicts, created only from
    verified external errors. No guessed missing permissions.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("AWARE_CLOCK_REQUIRED")
    taipei = now.astimezone(ZoneInfo("Asia/Taipei"))
    hhmm = taipei.hour * 100 + taipei.minute
    time_window_only = taipei.isoweekday() <= 5 and 900 <= hhmm < 1330
    blockers = user_blockers or {}
    routed, actionable, notify = [], [], []
    for item in details:
        number = item["number"]
        info = blockers.get(number)
        if info:
            if not isinstance(info, dict) or not info.get("action") or not info.get("url"):
                raise ValueError("INVALID_OPERATOR_REQUEST")
            state = "WAIT_USER"
            notify.append({"pr": number, "action": info["action"], "url": info["url"]})
        elif item["status"] == "CLOSED_VERIFY_GOVERNANCE":
            state = "REVIEW_CLOSED_EVIDENCE"
        elif item["ci_pending"] > 0:
            state = "WAIT_CI"
        elif item["work_window"] == "MARKET_SESSION":
            # An exchange calendar / real quote remains a separate hard gate.
            state = "WAIT_OFFICIAL_MARKET_CONFIRMATION" if time_window_only else "WAIT_MARKET"
        elif time_window_only:
            state = "DEFER_TO_OFF_MARKET"
        else:
            state = "READY_FOR_ENGINEERING"
            actionable.append(number)
        routed.append({"pr": number, "routing_state": state,
                       "next_action": item["next_action"],
                       "work_window": item["work_window"],
                       "head_sha": item["head_sha"]})
    return {"session_clock_only": time_window_only,
            "operator_notifications": notify,
            "next_off_market_engineering_prs": actionable,
            "queue": routed,
            "ready_is_not_repaired": True,
            "official_trading_day_confirmed": False}

def collect(fetch, now=None, user_blockers=None):
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
    routing = route_work_items(details, now, user_blockers)
    return {
        "schema": "SKY_W0_REPAIR_PROGRESS_V1",
        "routing": routing,
        "checked_at_utc": now.astimezone(timezone.utc).isoformat(),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "watchdog_cadence": "10_MINUTES_BEST_EFFORT_GITHUB_ACTIONS",
        "mode": "READ_ONLY_REPAIR_BACKLOG_NO_AUTONOMOUS_CODE_EDITS",
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
        "| PR | Work window | Next action | Status | CI pass | CI fail | CI pending |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for p in report["details"]:
        lines.append(f"| #{p['number']} | {p['work_window']} | {p['next_action']} | {p['status']} | {p['ci_success']} | {p['ci_failure']} | {p['ci_pending']} |")
    lines += ["", "## Work routing (no autonomous code edits)"]
    for item in report["routing"]["queue"]:
        lines.append("- PR #{}: {} — {}".format(item["pr"], item["routing_state"], item["next_action"]))
    if report["routing"]["operator_notifications"]:
        lines += ["", "## Operator actions — do not block independent repairs"]
        for item in report["routing"]["operator_notifications"]:
            lines.append("- PR #{}: {} — {}".format(item["pr"], item["action"], item["url"]))
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
