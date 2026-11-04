"""Read-only GitHub Actions latency and scan-health monitor (P0-OPS)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKFLOWS = (
    "scan.yml",
    "swing-live-scan.yml",
    "shadow-promotion-dashboard.yml",
)
QUEUE_WARNING_SEC = 300
RUNTIME_WARNING_SEC = 600
SCAN_REQUIRED = {"scan.yml", "swing-live-scan.yml"}


def parse_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def seconds_between(first, second):
    a, b = parse_time(first), parse_time(second)
    return max(0, round((b - a).total_seconds())) if a and b else None


def api_json(url, token):
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "sky-p0ops-monitor",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def summarize_run(run, job):
    # run_started_at may equal created_at even when the job waits for a runner.
    # Job started_at is used for the real enqueue-to-run measurement.
    job_started = job.get("started_at") if job else None
    job_ended = job.get("completed_at") if job else None
    return {
        "run_id": run["id"],
        "url": run.get("html_url"),
        "event": run.get("event"),
        "created_at_utc": run.get("created_at"),
        "job_started_at_utc": job_started,
        "job_completed_at_utc": job_ended,
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "queue_seconds": seconds_between(run.get("created_at"), job_started),
        "job_seconds": seconds_between(job_started, job_ended),
        "failed_steps": [
            step.get("name")
            for step in (job or {}).get("steps", [])
            if step.get("conclusion") in {"failure", "timed_out"}
        ],
    }


def assess(workflow, rows):
    alerts = []
    if not rows:
        return ["NO_COMPLETED_RUN_FOUND"]
    latest = rows[0]
    if latest["conclusion"] not in {"success", "skipped"}:
        alerts.append("LATEST_RUN_FAILED")
    if latest["queue_seconds"] is not None and latest["queue_seconds"] > QUEUE_WARNING_SEC:
        alerts.append("RUNNER_QUEUE_OVER_5M")
    if latest["job_seconds"] is not None and latest["job_seconds"] > RUNTIME_WARNING_SEC:
        alerts.append("JOB_RUNTIME_OVER_10M")
    if workflow in SCAN_REQUIRED and len(rows) >= 2 and all(
        r["conclusion"] != "success" for r in rows[:2]
    ):
        alerts.append("CONSECUTIVE_SCAN_FAILURES")
    return alerts


def collect(repo, token):
    base = f"https://api.github.com/repos/{repo}/actions"
    results, warnings = {}, {}
    for workflow in WORKFLOWS:
        escaped = urllib.parse.quote(workflow, safe="")
        payload = api_json(
            f"{base}/workflows/{escaped}/runs?per_page=15&branch=main", token
        )
        # Restrict to completed runs, never confuse queued/in-progress with failure.
        runs = [r for r in payload.get("workflow_runs", []) if r.get("status") == "completed"][:5]
        rows = []
        for run in runs:
            jobs_payload = api_json(f"{base}/runs/{run['id']}/jobs?per_page=100", token)
            jobs = jobs_payload.get("jobs", [])
            job = min(jobs, key=lambda j: j.get("started_at") or "9999") if jobs else None
            rows.append(summarize_run(run, job))
        results[workflow] = rows
        warnings[workflow] = assess(workflow, rows)
    return results, warnings


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    now = datetime.now(timezone.utc).isoformat()
    try:
        results, warnings = collect(repo, token)
        payload = {
            "schema": "SKY_P0OPS_ACTIONS_LATENCY_V1",
            "generated_at_utc": now,
            "repository": repo,
            "source": "GitHub Actions REST API; completed main-branch runs",
            "measurements": results,
            "warnings": warnings,
            "monitor_status": "WARNING" if any(warnings.values()) else "PASS",
            "production_modified": False,
        }
    except (urllib.error.URLError, ValueError, KeyError) as exc:
        payload = {
            "schema": "SKY_P0OPS_ACTIONS_LATENCY_V1",
            "generated_at_utc": now,
            "repository": repo,
            "monitor_status": "INSUFFICIENT_DATA",
            "error_type": type(exc).__name__,
            "production_modified": False,
        }

    dest = Path("output/p0ops/actions_latency.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["## Sky P0-OPS Actions latency monitor", "", f"UTC: {now}",
             f"Status: **{payload['monitor_status']}**", ""]
    for name, rows in payload.get("measurements", {}).items():
        last = rows[0] if rows else {}
        lines.append(f"- {name}: {last.get('conclusion', 'UNKNOWN')}; "
                     f"queue={last.get('queue_seconds', 'N/A')}s; "
                     f"job={last.get('job_seconds', 'N/A')}s; "
                     f"alerts={','.join(payload['warnings'][name]) or 'none'}")
    lines += ["", "Run and report: GitHub Actions artifact `p0ops-latency-<run-id>`.",
              "This monitor does not change trading signals, models or schedules."]
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
            stream.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    # Monitoring failure must be visible, not silently treated as healthy.
    return 2 if payload["monitor_status"] == "INSUFFICIENT_DATA" else 0


if __name__ == "__main__":
    sys.exit(main())
