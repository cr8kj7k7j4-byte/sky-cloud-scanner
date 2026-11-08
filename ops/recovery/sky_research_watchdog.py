"""Bounded, fail-closed GitHub Actions watchdog for isolated research CI only.

Does NOT resume ChatGPT sessions, dispatch trading workflows, or change Production.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

SAFE_WORKFLOWS = ("four-strategy-research-contract.yml",)
DEFAULT_CUTOFF = "2026-11-09T22:31:00+00:00"  # 2026-11-10 06:31 Asia/Taipei
MAX_ATTEMPTS = 3  # original attempt + at most two retries


def utc_time(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timezone_required")
    return dt.astimezone(timezone.utc)


def decide_retry(run, now, cutoff, max_attempts=MAX_ATTEMPTS):
    """Pure decision; never dispatch or mutate. Returns an action and reason."""
    if now >= cutoff:
        return ("skip", "expired")
    if not run:
        return ("skip", "no_run")
    if run.get("status") != "completed":
        return ("skip", "already_active")
    if run.get("conclusion") not in ("failure", "timed_out"):
        return ("skip", "not_retryable_conclusion")
    try:
        attempts = int(run["run_attempt"])
        created = utc_time(run["created_at"])
    except (ValueError, TypeError, KeyError):
        return ("skip", "missing_run_evidence")
    if isinstance(run["run_attempt"], bool) or attempts < 1:
        return ("skip", "invalid_attempt")
    if attempts >= max_attempts:
        return ("skip", "attempt_limit")
    if created > now + timedelta(minutes=2) or now - created > timedelta(hours=24):
        return ("skip", "stale_or_future_run")
    if run.get("event") != "pull_request":
        return ("skip", "not_pr_ci")
    if not isinstance(run.get("id"), int) or isinstance(run["id"], bool) or run["id"] < 1:
        return ("skip", "invalid_run_id")
    return ("retry", "failed_allowlisted_pr_ci")


def api(method, url, token):
    request = urllib.request.Request(
        url, method=method,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "sky-24h-research-watchdog"})
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read()
        return json.loads(body) if body else {}


def check_once(fetch, retry, now, cutoff, enabled):
    """Inject network functions for isolated and deterministic tests."""
    result = {"checked_at": now.isoformat(), "cutoff_at": cutoff.isoformat(),
              "expired": now >= cutoff, "items": [], "retry_enabled": enabled}
    for workflow in SAFE_WORKFLOWS:
        item = {"workflow": workflow}
        if now >= cutoff:
            item.update(action="skip", reason="expired")
            result["items"].append(item)
            continue
        try:
            runs = fetch(workflow)
            run = runs[0] if runs else None
            action, reason = decide_retry(run, now, cutoff)
            item.update(action=action, reason=reason,
                        run_id=run.get("id") if run else None,
                        run_attempt=run.get("run_attempt") if run else None,
                        run_conclusion=run.get("conclusion") if run else None)
            if action == "retry":
                if enabled:
                    retry(workflow, run["id"])
                    item["action"] = "retry_requested"
                else:
                    item["action"] = "dry_run"
            result["items"].append(item)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                KeyError, TypeError, ValueError) as exc:
            item.update(action="error", reason=type(exc).__name__)
            result["items"].append(item)
    return result


def main():
    token = os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo or "/" not in repo:
        raise SystemExit("missing_github_context")
    now = datetime.now(timezone.utc)
    cutoff = utc_time(os.environ.get("SKY_RECOVERY_END_UTC", DEFAULT_CUTOFF))
    # All active retries are limited to allowlisted test-only PR CI.
    enabled = os.environ.get("SKY_RECOVERY_RETRY_ENABLED", "false").lower() == "true"
    root = "https://api.github.com/repos/" + repo

    def fetch(workflow):
        uri = urllib.parse.quote(workflow, safe="")
        data = api("GET", root + "/actions/workflows/" + uri +
                   "/runs?per_page=5&event=pull_request", token)
        return data.get("workflow_runs", [])

    def retry(workflow, run_id):
        api("POST", root + "/actions/runs/" + str(run_id) + "/rerun-failed-jobs", token)

    report = check_once(fetch, retry, now, cutoff, enabled)
    os.makedirs("recovery-reports", exist_ok=True)
    with open("recovery-reports/latest.json", "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))
    # Do not auto-retry unrecognized API failures or falsify success.
    if any(i["action"] == "error" for i in report["items"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
