"""Read-only 24h GitHub Actions monitor for the W0 research schedule handoff.

This does not run, fix, or restart paid jobs. It cannot prove a future schedule
before that event occurs and never claims production signal eligibility.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")
DEADLINE = datetime(2026, 11, 9, 10, 38, tzinfo=TPE)
TARGET_WORKFLOWS = (
    "three-model-research-daily-dispatch.yml",
    "three-model-evening-health.yml",
    "three-model-fugle-private-ledger.yml",
    "three-model-next-session-markout.yml",
)
FAILURES = frozenset(("failure", "cancelled", "timed_out", "action_required"))
OUT = Path("output/w0_research_quickwatch")


def parse_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def evaluate(now, results, *, lookback_minutes=15):
    """Review the recent main-branch runs without assuming schedule is proven."""
    if now.tzinfo is None:
        raise ValueError("now must have an explicit timezone")
    base = {
        "schema": "SKY_W0_RESEARCH_QUICKWATCH_V1",
        "observed_at_tpe": now.astimezone(TPE).isoformat(),
        "deadline_tpe": DEADLINE.isoformat(),
        "monitor_scope": "GITHUB_ACTIONS_READ_ONLY",
        "production_signal": False,
        "trading_enabled": False,
        "scheduled_17_30_18_30_19_45_verified": False,
        "note": "PR CI and manual dispatch never prove event=schedule. Scheduled research slots occur after this monitor deadline.",
    }
    if now.astimezone(TPE) >= DEADLINE:
        return {**base, "status": "MONITOR_WINDOW_EXPIRED", "anomalies": [], "runs": []}
    cutoff = now.astimezone(timezone.utc) - timedelta(minutes=lookback_minutes)
    anomalies, observed = [], []
    for workflow in TARGET_WORKFLOWS:
        for run in results.get(workflow, []):
            if run.get("head_branch") != "main" or run.get("event") == "pull_request":
                continue
            when = parse_time(run.get("created_at"))
            if when is None or when < cutoff or when > now.astimezone(timezone.utc) + timedelta(minutes=1):
                continue
            status = run.get("status")
            conclusion = run.get("conclusion")
            record = {
                "workflow": workflow, "run_id": run.get("id"),
                "event": run.get("event"), "status": status,
                "conclusion": conclusion, "url": run.get("html_url"),
                "created_at": run.get("created_at"),
            }
            observed.append(record)
            if status == "completed" and conclusion in FAILURES:
                anomalies.append(record)
    return {
        **base, "status": "ANOMALY_DETECTED" if anomalies else "NO_RECENT_FAILED_MAIN_RUNS",
        "anomalies": anomalies, "runs": observed,
    }


def github_get(repo, workflow, token):
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs?per_page=15&branch=main"
    request = Request(
        url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Sky-W0-Research-Quickwatch",
        },
    )
    with urlopen(request, timeout=15) as response:
        payload = json.load(response)
    if not isinstance(payload.get("workflow_runs"), list):
        raise ValueError("INVALID_GITHUB_ACTIONS_RUN_RESPONSE")
    return payload["workflow_runs"]


def main():
    now = datetime.now(timezone.utc)
    if now.astimezone(TPE) >= DEADLINE:
        result = evaluate(now, {})
    else:
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        token = os.environ.get("GITHUB_TOKEN", "")
        if not repo or not token:
            result = {
                "schema": "SKY_W0_RESEARCH_QUICKWATCH_V1",
                "status": "MONITOR_BLOCKED_CONFIGURATION",
                "observed_at_tpe": now.astimezone(TPE).isoformat(),
                "reason": "MISSING_GITHUB_REPOSITORY_OR_TOKEN",
                "production_signal": False, "trading_enabled": False,
            }
        else:
            try:
                results = {w: github_get(repo, w, token) for w in TARGET_WORKFLOWS}
                result = evaluate(now, results)
            except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                result = {
                    "schema": "SKY_W0_RESEARCH_QUICKWATCH_V1",
                    "status": "MONITOR_BLOCKED_GITHUB_API",
                    "observed_at_tpe": now.astimezone(TPE).isoformat(),
                    "error_type": type(exc).__name__,
                    "production_signal": False, "trading_enabled": False,
                }
    OUT.mkdir(parents=True, exist_ok=True)
    file = OUT / "latest.json"
    file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Step outputs are deliberately only state, not bearer tokens or raw API.
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as output:
            output.write(f"result={result['status']}\n")
    print(json.dumps({"status": result["status"], "report": str(file)}, ensure_ascii=False))
    return 1 if result["status"].startswith(("ANOMALY_", "MONITOR_BLOCKED_")) else 0


if __name__ == "__main__":
    sys.exit(main())
