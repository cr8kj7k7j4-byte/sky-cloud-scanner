"""W2 research-only short-lived GitHub Actions watchdog.

No Fugle/GCS access, no automatic replay, no production writes.
Actions cron is best effort; a five-minute expression is not a five-minute SLA.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

START = datetime(2026, 11, 8, 2, 38, tzinfo=timezone.utc)
END = datetime(2026, 11, 9, 2, 38, tzinfo=timezone.utc)  # TPE 11/09 10:38
WORKFLOWS = (
    "three-model-research-daily-dispatch.yml",
    "three-model-fugle-private-ledger.yml",
    "three-model-next-session-markout.yml",
    "three-model-evening-health.yml",
)
WATCHDOG = "w2-research-24h-watchdog.yml"
ISSUE_NUMBER = 360
API = "https://api.github.com"


def _when(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def assess(now, by_workflow):
    """Review only new, main-branch research runs; no missing-run assertion pre-slot."""
    failures = []
    observed = 0
    for workflow in WORKFLOWS:
        for run in by_workflow.get(workflow, []):
            if run.get("head_branch") != "main":
                continue
            if run.get("event") not in ("schedule", "workflow_dispatch"):
                continue
            try:
                created = _when(run["created_at"])
            except (KeyError, TypeError, ValueError):
                continue
            if not START <= created < END or created > now:
                continue
            observed += 1
            state, conclusion = run.get("status"), run.get("conclusion")
            reason = None
            if state == "completed" and conclusion != "success":
                reason = "COMPLETED_NOT_SUCCESSFUL"
            elif state != "completed" and now - created > timedelta(minutes=45):
                reason = "RUN_STALLED_OVER_45_MIN"
            if reason:
                failures.append({
                    "workflow": workflow, "run_id": run.get("id"), "event": run.get("event"),
                    "created_at": run["created_at"], "conclusion": conclusion,
                    "reason": reason, "url": run.get("html_url"),
                })
    return {"schema": "W2_RESEARCH_24H_WATCHDOG_V1",
            "checked_at_utc": now.isoformat(), "window_start_utc": START.isoformat(),
            "window_end_utc": END.isoformat(), "observed_runs": observed,
            "failures": failures, "status": "ATTENTION" if failures else "NO_CONFIRMED_FAILURE",
            "schedule_identity_verified": False, "gcs_readback_verified": False,
            "trading_enabled": False, "production_changed": False}


def _api(method, path, body=None):
    repo = os.environ["GITHUB_REPOSITORY"]
    if not repo or repo.count("/") != 1:
        raise ValueError("invalid_repository")
    url = f"{API}/repos/{repo}/{path.lstrip('/')}"
    headers = {
        "Authorization": "Bearer " + os.environ["GH_TOKEN"],
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "sky-w2-research-watchdog",
    }
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, headers=headers, data=payload, method=method)
    with urlopen(req, timeout=20) as response:
        raw = response.read()
    return json.loads(raw) if raw else {}


def alert_once(failure):
    """Persist one comment per failure fingerprint; read-before-write dedup."""
    key = f"W2_WATCHDOG_EVENT:{failure['workflow']}:{failure['run_id']}:{failure['reason']}"
    comments = _api("GET", f"issues/{ISSUE_NUMBER}/comments?per_page=100")
    if any(key in str(item.get("body", "")) for item in comments):
        return "ALREADY_RECORDED"
    body = ("W2 24h research-only watchdog: confirmed workflow anomaly.\n\n"
            f"- Fingerprint: `{key}`\n"
            f"- Run: {failure.get('url') or 'URL_NOT_AVAILABLE'}\n"
            f"- Event: {failure['event']}\n"
            f"- Result: {failure['reason']} / {failure['conclusion']}\n"
            "- Automated paid Fugle/GCS rerun: NO (not yet safe/authorized).\n"
            "- Production/trades changed: NO. W0/W2 review required.")
    _api("POST", f"issues/{ISSUE_NUMBER}/comments", {"body": body})
    return "ISSUE_COMMENT_CREATED"


def main():
    now = datetime.now(timezone.utc)
    out = Path("output/w2_research_24h_watchdog")
    out.mkdir(parents=True, exist_ok=True)
    if now >= END:
        # Expire this short-lived pilot instead of consuming Actions indefinitely.
        # Only this watchdog workflow is disabled, never the three model schedules.
        _api("PUT", f"actions/workflows/{WATCHDOG}/disable")
        result = {"status": "EXPIRED_SELF_DISABLED", "checked_at_utc": now.isoformat(),
                  "production_changed": False, "trading_enabled": False}
    elif now < START:
        result = {"status": "BEFORE_WINDOW", "checked_at_utc": now.isoformat(),
                  "production_changed": False, "trading_enabled": False}
    else:
        runs = {}
        for name in WORKFLOWS:
            data = _api("GET", f"actions/workflows/{name}/runs?per_page=50")
            runs[name] = data.get("workflow_runs", [])
        result = assess(now, runs)
        result["issue_updates"] = [alert_once(f) for f in result["failures"]]
    (out / "latest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "failures": len(result.get("failures", [])),
                      "production_changed": False}))
    # GitHub Actions red status is an additional durable alarm.
    if result["status"] == "ATTENTION":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
