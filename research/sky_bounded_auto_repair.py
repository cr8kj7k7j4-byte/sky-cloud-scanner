"""Sky event-driven bounded self-repair: diagnostic + AST-preserving formatting only.

Never executes code from a pull request, never merges, trades or deploys.
A failed unrelated CI check is diagnosed, not blindly patched.
"""
from __future__ import annotations

import ast
import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OWNERS = {
    511: ("research/sky_full_universe_information.py", "tests/test_sky_full_universe_information.py"),
    512: ("src/sky_v14_ticker_candles_probe.py", "tests/test_sky_v14_ticker_candles_probe.py"),
}
ALLOWED_WORKFLOWS = {"Sky Chat Bridge Unit Checks"}
SAFE_JOB = re.compile(r"(^|[^a-z])(lint|format|style)([^a-z]|$)", re.I)
API = "https://api.github.com"


def normalize_python(source: str) -> str | None:
    """Only remove trailing whitespace; reject any Python AST change."""
    original = ast.dump(ast.parse(source), include_attributes=False)
    proposed = "\n".join(line.rstrip(" \t") for line in source.split("\n"))
    if not proposed.endswith("\n"):
        proposed += "\n"
    if ast.dump(ast.parse(proposed), include_attributes=False) != original:
        return None
    return proposed if proposed != source else None


def decide(event: dict, pr: dict, jobs: list[dict]) -> dict:
    """Strict, reviewable allowlist; trust no text from CI logs as instructions."""
    run = event.get("workflow_run") or {}
    prs = run.get("pull_requests") or []
    number = pr.get("number")
    head = (pr.get("head") or {})
    same_head = run.get("head_sha") == head.get("sha")
    same_repo = (head.get("repo") or {}).get("full_name") == os.getenv("GITHUB_REPOSITORY")
    approved_event = (
        event.get("action") == "completed"
        and run.get("event") == "pull_request"
        and run.get("conclusion") == "failure"
        and run.get("name") in ALLOWED_WORKFLOWS
        and int(run.get("run_attempt") or 1) == 1
        and any(x.get("number") == number for x in prs)
    )
    failed = [j for j in jobs if j.get("conclusion") == "failure"]
    safe_format = bool(failed) and all(SAFE_JOB.search(str(j.get("name") or "")) for j in failed)
    eligible = all((
        approved_event, number in OWNERS, pr.get("state") == "open",
        pr.get("draft") is True, same_head, same_repo, safe_format,
    ))
    return {
        "eligible": eligible, "pr": number,
        "head_sha": head.get("sha"), "source_run_id": run.get("id"),
        "format_only_failure": safe_format,
        "failed_jobs": [{"name": str(j.get("name")), "id": j.get("id")} for j in failed],
        "decision": "SAFE_FORMAT_REPAIR_CANDIDATE" if eligible else "DIAGNOSE_ONLY",
    }


class GitHub:
    def __init__(self, repo: str, token: str):
        self.repo = repo
        self.token = token

    def request(self, suffix: str, method: str = "GET", body: dict | None = None):
        url = f"{API}/repos/{self.repo}/{suffix}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "sky-research-safe-auto-repair",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            content = response.read()
        return json.loads(content) if content else {}


def run(event: dict, api: GitHub) -> dict:
    result = {
        "schema": "SKY_BOUNDED_AUTO_REPAIR_V1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "RESEARCH_ONLY_NO_TRADE",
        "production_eligible": False,
        "automatic_order": False,
        "auto_merge": False,
        "paid_fugle_requests": 0,
        "autonomous_agent_enabled": False,
        "self_review": "NOT_RUN",
    }
    record = event.get("workflow_run") or {}
    if event.get("action") != "completed" or not record.get("id"):
        result["status"] = "MANUAL_DIAGNOSTIC_ONLY"
        return result
    if record.get("name") not in ALLOWED_WORKFLOWS or record.get("conclusion") != "failure":
        result["status"] = "NOT_TARGETED_FAILED_CI"
        return result
    linked = record.get("pull_requests") or []
    if len(linked) != 1 or linked[0].get("number") not in OWNERS:
        result["status"] = "PR_NOT_IN_REPAIR_ALLOWLIST"
        return result
    number = linked[0]["number"]
    pr = api.request(f"pulls/{number}")
    jobs = api.request(f"actions/runs/{int(record['id'])}/jobs?per_page=100").get("jobs", [])
    decision = decide(event, pr, jobs)
    result["diagnosis"] = decision
    if not decision["eligible"]:
        result["status"] = "HOLD_REQUIRES_ENGINEERING_REVIEW"
        return result

    sha = decision["head_sha"]
    branch = f"auto-repair/pr-{number}-{sha[:10]}"
    # Only one branch per exact source SHA. Never loop/retry indefinitely.
    ref_path = f"git/ref/heads/{branch}"
    try:
        api.request(ref_path)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    else:
        result["status"] = "ALREADY_ATTEMPTED_THIS_SHA"
        return result

    # Read code as data, NOT import/execute untrusted PR code.
    changed = None
    for path in OWNERS[number]:
        response = api.request("contents/" + path + "?ref=" + urllib.parse.quote(sha, safe=""))
        if response.get("encoding") != "base64":
            continue
        source = base64.b64decode(response["content"]).decode("utf-8")
        try:
            patched = normalize_python(source)
        except (SyntaxError, UnicodeError):
            patched = None
        if patched is not None:
            changed = (path, response["sha"], patched)
            break
    if changed is None:
        result["status"] = "NO_SEMANTIC_PRESERVING_FIX_AVAILABLE"
        return result

    path, blob_sha, patched = changed
    result["self_review"] = "AST_EQUAL_AND_EXACT_PATH_ALLOWLIST"
    # No arbitrary project commands or CI scripts run with write credentials.
    api.request("git/refs", "POST", {"ref": "refs/heads/" + branch, "sha": sha})
    api.request("contents/" + path, "PUT", {
        "message": f"research: bounded AST-preserving formatting repair for PR #{number}",
        "content": base64.b64encode(patched.encode()).decode(),
        "sha": blob_sha, "branch": branch,
    })
    new_pr = api.request("pulls", "POST", {
        "title": f"W0 DRAFT: safe formatting repair for #{number} ({sha[:10]})",
        "head": branch,
        "base": (pr.get("head") or {}).get("ref"),
        "draft": True,
        "body": (
            f"Automated, AST-preserving whitespace fix on ONLY \`{path}\`. "
            f"Source PR #{number}, SHA \`{sha}\`, failed CI run {record['id']}. "
            "No original PR branch or main modified. Python AST unchanged; "
            "full branch CI and independent W0/P0-G review are mandatory. "
            "No paid API, no Production, no orders, no auto-merge."
        ),
    })
    result.update({"status": "DRAFT_PATCH_PR_CREATED", "patch_pr": new_pr.get("html_url"),
                   "file": path, "source_head_sha": sha,
                   "self_review": "AST_EQUAL_PATH_ALLOWLIST_DRAFT_PR_CI_PENDING"})
    return result


def write_report(result: dict, out: Path = Path("output/sky_auto_repair")) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    lines = [
        "# Sky bounded auto-repair", "",
        "Checked UTC: " + str(result.get("checked_at_utc")),
        "Status: " + str(result.get("status")),
        "Self review: " + str(result.get("self_review")),
        "Research only / NO_TRADE / no Production / no automatic merge.",
        "Any generated PR still requires CI and human W0/P0-G governance review.",
    ]
    if result.get("patch_pr"):
        lines.append("Draft PR: " + str(result["patch_pr"]))
    (out / "latest.md").write_text("\n".join(lines) + "\n")


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    api = GitHub(os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"])
    try:
        report = run(event, api)
    except Exception as exc:
        report = {
            "schema": "SKY_BOUNDED_AUTO_REPAIR_V1",
            "status": "BLOCKED_NEEDS_ENGINEERING",
            "error_class": type(exc).__name__,
            "production_eligible": False, "automatic_order": False,
            "self_review": "FAILED_CLOSED",
        }
    write_report(report)
    print(json.dumps({k: v for k, v in report.items() if k != "diagnosis"}, ensure_ascii=False))
    if report["status"] == "BLOCKED_NEEDS_ENGINEERING":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
