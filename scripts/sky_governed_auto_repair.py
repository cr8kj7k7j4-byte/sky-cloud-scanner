"""Governed Sky self-repair: deterministic allowlist only, no production promotion.

No schedules, market-data requests, order execution or model/risk-rule changes.
Auto repair writes a distinct research branch + draft PR only.  No arbitrary LLM edits.
"""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

TARGET_PR = 511
TARGET_BRANCH = "research/fugle-snapshot-diagnostics-20261110"
TARGET_FILE = ".github/workflows/sky-snapshot-integrity-research-acceptance.yml"
OUTPUT = Path("output/sky_governed_auto_repair/latest.json")
# Dedicated non-market, research-only fixture. This branch never targets main
# for auto repair. It is not a second auto-repair engine.
SMOKE_BRANCH = "research/sky-governed-smoke-acceptance-20261111"
SMOKE_FILE = "research/sky_governed_auto_repair_smoke_fixture.txt"
SMOKE_BROKEN = "SKY_GOVERNED_SMOKE_BROKEN_V1\n"
SMOKE_FIXED = "SKY_GOVERNED_SMOKE_FIXED_V1\n"

# The exact two known-safe changes are allowed, nothing else.
OLD = """SHA=$(gh api "$TARGET" --jq '.sha' 2>/dev/null || true)"""
NEW = """SHA=$(gh api "$TARGET?ref=research/fugle-snapshot-diagnostics-20261110" --jq '.sha' 2>/dev/null || true)"""
ARTIFACT_WARN = "if-no-files-found: warn"
ARTIFACT_ERROR = "if-no-files-found: error"


def safe_patch(source: str) -> tuple[str, list[str]]:
    """Only deterministic evidence-publication safety changes to one workflow."""
    out = source
    fixes = []
    if OLD in out:
        if out.count(OLD) != 1:
            raise ValueError("AMBIGUOUS_SHA_LOOKUP")
        out = out.replace(OLD, NEW)
        fixes.append("FIX_BRANCH_SPECIFIC_RECEIPT_SHA_409")
    # Only change the one artifact upload policy if present.
    if ARTIFACT_WARN in out:
        if out.count(ARTIFACT_WARN) != 1:
            raise ValueError("AMBIGUOUS_ARTIFACT_UPLOAD_POLICY")
        out = out.replace(ARTIFACT_WARN, ARTIFACT_ERROR)
        fixes.append("FAIL_CLOSED_MISSING_ARTIFACT")
    if out != source:
        assert not any(line.startswith("  schedule:") for line in out.splitlines()), "SCHEDULE_CHANGE_DISALLOWED"
    return out, fixes


def review(before: str, after: str, fixes: list[str]) -> dict:
    """Fail closed on unapproved file changes, automatic merge, or regression."""
    expected, expected_fixes = safe_patch(before)
    passed = after == expected and fixes == expected_fixes
    return {"status": "PASS" if passed else "REJECT", "safe_patch_only": passed,
            "research_only": True, "production_eligible": False,
            "automatic_order": False, "automatic_merge": False}


class Github:
    def __init__(self, repo: str, token: str):
        if not token or not repo or "/" not in repo:
            raise ValueError("GITHUB_AUTH_OR_REPO_MISSING")
        self.repo = repo
        self.base = "https://api.github.com/repos/" + repo
        self.headers = {"Authorization": "Bearer " + token,
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "Sky-Governed-Auto-Repair",
                        "X-GitHub-Api-Version": "2022-11-28"}

    def call(self, path: str, method: str = "GET", body: dict | None = None):
        raw = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self.base + path, data=raw, method=method,
            headers={**self.headers, **({"Content-Type": "application/json"} if raw is not None else {})})
        with urllib.request.urlopen(req, timeout=20) as response:
            b = response.read()
            return json.loads(b.decode("utf-8")) if b else {}


def run(api: Github, *, allow_write: bool, event_name: str, expected_sha: str | None = None) -> dict:
    report = {"schema": "SKY_GOVERNED_AUTO_REPAIR_V1",
              "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "trigger": event_name, "mode": "SAFE_PATCH" if allow_write else "DIAGNOSE_ONLY",
              "target_pr": TARGET_PR, "research_only": True,
              "production_eligible": False, "automatic_order": False,
              "automatic_merge": False, "paid_api_calls": 0,
              "state": "HOLD", "blockers": [], "applied_fixes": []}
    pr = api.call(f"/pulls/{TARGET_PR}")
    if pr.get("state") != "open" or not pr.get("draft", False) or pr.get("merged", False):
        report["blockers"].append("TARGET_PR_NOT_OPEN_DRAFT")
        return report
    head = pr["head"]
    sha = head["sha"]
    report["target_sha"] = sha
    if expected_sha is not None and (not expected_sha or sha != expected_sha):
        report["blockers"].append("TRIGGER_SHA_NOT_CURRENT_PR_HEAD")
        return report
    if (head.get("repo") or {}).get("full_name") != api.repo:
        report["blockers"].append("TARGET_REPOSITORY_NOT_TRUSTED")
        return report
    if head["ref"] != TARGET_BRANCH:
        report["blockers"].append("TARGET_BRANCH_CHANGED")
        return report
    path = "/contents/" + TARGET_FILE + "?ref=" + sha
    doc = api.call(path)
    before = base64.b64decode(doc["content"]).decode("utf-8")
    after, fixes = safe_patch(before)
    report["candidate_fixes"] = fixes
    report["self_review"] = review(before, after, fixes)
    if report["self_review"]["status"] != "PASS":
        report["blockers"].append("SELF_REVIEW_REJECT")
        return report
    if not fixes:
        report["blockers"].append("NO_ALLOWLISTED_REPAIR_NEEDED")
        report["blockers"].append("LIVE_QUOTE_AND_W0_P0G_GATES_STILL_OPEN")
        return report
    if not allow_write:
        report["state"] = "PATCH_READY_FOR_DRAFT_PR"
        return report
    # Fail closed if the owning PR advanced after the initial read.  All patch
    # source bytes above came from immutable SHA, not a mutable branch name.
    latest = api.call(f"/pulls/{TARGET_PR}")
    if (latest.get("head") or {}).get("sha") != sha:
        report["blockers"].append("TARGET_PR_HEAD_CHANGED_BEFORE_PATCH")
        return report
    # Never update production or the target branch. Draft PR targets research head.
    branch = "research/sky-auto-repair-pr511-" + sha[:12]
    try:
        api.call("/git/refs", "POST", {"ref": "refs/heads/" + branch, "sha": sha})
        report["created_repair_branch"] = branch
    except urllib.error.HTTPError as exc:
        if exc.code == 422:
            report["blockers"].append("REPAIR_BRANCH_ALREADY_EXISTS_MANUAL_REVIEW")
            return report
        raise
    encoded = base64.b64encode(after.encode("utf-8")).decode("ascii")
    api.call("/contents/" + TARGET_FILE, "PUT", {
        "message": "repair: deterministic receipt SHA / artifact safety [research only]",
        "content": encoded, "sha": doc["sha"], "branch": branch})
    new_pr = api.call("/pulls", "POST", {
        "title": "AUTO-REPAIR RESEARCH: bounded Snapshot receipt publication fix",
        "head": branch, "base": TARGET_BRANCH, "draft": True,
        "body": ("Automated deterministic allowlist patch only. Fixes: " + ", ".join(fixes)
                 + ". Self-review PASS. CI and W0/P0-G review required. "
                 + "No market API calls, no automatic merge, no Production changes.")})
    report["applied_fixes"] = fixes
    report["repair_pr"] = new_pr.get("html_url")
    report["state"] = "DRAFT_REPAIR_PR_CREATED_AWAITING_CI_AND_W0_P0G"
    return report



def run_smoke(api: Github, *, expected_sha: str, allow_write: bool,
              linked_prs: list) -> dict:
    """Repair one isolated CI smoke fixture; no market, PR #511 or main writes."""
    result = {
        "schema": "SKY_GOVERNED_AUTO_REPAIR_V1",
        "mode": "BOUNDED_SMOKE_E2E",
        "trigger": "workflow_run",
        "research_only": True, "production_eligible": False,
        "automatic_order": False, "automatic_merge": False,
        "paid_api_calls": 0, "state": "HOLD", "blockers": [],
        "candidate_fixes": [], "applied_fixes": [],
        "source_sha": expected_sha,
    }
    if not expected_sha or len(expected_sha) != 40:
        result["blockers"].append("INVALID_SMOKE_SHA")
        return result
    # Query exactly one open PR for a fixed, non-production branch.
    owner = api.repo.partition("/")[0]
    prs = api.call("/pulls?state=open&head=" + owner + ":" + SMOKE_BRANCH + "&per_page=10")
    if not isinstance(prs, list) or len(prs) != 1:
        result["blockers"].append("SMOKE_PR_NOT_UNIQUE")
        return result
    pr = prs[0]
    pr_number = pr.get("number")
    head = pr.get("head") or {}
    if (pr.get("state") != "open" or not pr.get("draft")
            or (pr.get("base") or {}).get("ref") != "main"
            or head.get("ref") != SMOKE_BRANCH
            or (head.get("repo") or {}).get("full_name") != api.repo
            or head.get("sha") != expected_sha
            or not isinstance(pr_number, int)
            or (linked_prs and (len(linked_prs) != 1
                                or linked_prs[0].get("number") != pr_number))):
        result["blockers"].append("SMOKE_PR_IDENTITY_OR_SHA_INVALID")
        return result
    result["target_pr"] = pr_number
    result["target_sha"] = expected_sha
    doc = api.call("/contents/" + SMOKE_FILE + "?ref=" + expected_sha)
    raw = base64.b64decode(doc["content"]).decode("utf-8")
    if raw == SMOKE_FIXED:
        result["blockers"].append("NO_SMOKE_REPAIR_NEEDED")
        return result
    if raw != SMOKE_BROKEN:
        result["blockers"].append("UNAPPROVED_SMOKE_CONTENT")
        return result
    result["candidate_fixes"] = ["FIX_ISOLATED_SMOKE_FIXTURE_ONLY"]
    result["self_review"] = {
        "status": "PASS", "exact_allowlist": True,
        "production_eligible": False, "automatic_merge": False,
    }
    if not allow_write:
        result["state"] = "SMOKE_PATCH_READY_NO_WRITE"
        return result
    # Fresh SHA before any write; unrelated branch changes fail closed.
    current = api.call("/pulls/" + str(pr_number))
    if ((current.get("head") or {}).get("sha") != expected_sha
            or not current.get("draft")
            or current.get("state") != "open"):
        result["blockers"].append("SMOKE_PR_CHANGED_BEFORE_WRITE")
        return result
    repair_branch = "research/sky-governed-smoke-fixed-" + expected_sha[:12]
    try:
        api.call("/git/refs", "POST",
                 {"ref": "refs/heads/" + repair_branch, "sha": expected_sha})
    except urllib.error.HTTPError as exc:
        if exc.code == 422:
            result["blockers"].append("SMOKE_BRANCH_EXISTS_NO_REPEAT")
            return result
        raise
    api.call("/contents/" + SMOKE_FILE, "PUT", {
        "message": "test: deterministic smoke fixture safe correction [no trade]",
        "content": base64.b64encode(SMOKE_FIXED.encode("utf-8")).decode("ascii"),
        "sha": doc["sha"], "branch": repair_branch,
    })
    result["repair_branch"] = repair_branch
    try:
        created = api.call("/pulls", "POST", {
        "title": "DRAFT: governed research-only smoke fixture repair",
        "head": repair_branch, "base": SMOKE_BRANCH, "draft": True,
        "body": ("Non-market, deterministic one-file smoke acceptance only; "
                 "source SHA " + expected_sha + ". Run downstream CI and read "
                 "GitHub artifact before considering E2E verified. No auto-merge."),
        })
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            result["blockers"].append("GITHUB_TOKEN_DRAFT_PR_PERMISSION_403")
            result["state"] = "HOLD_DRAFT_PR_PERMISSION"
            result["applied_fixes"] = ["FIX_ISOLATED_SMOKE_FIXTURE_ONLY"]
            return result
        raise
    result["repair_pr"] = created.get("html_url")
    result["repair_pr_number"] = created.get("number")
    result["applied_fixes"] = ["FIX_ISOLATED_SMOKE_FIXTURE_ONLY"]
    # GITHUB_TOKEN-created PRs do not cause automatic pull_request CI.
    # workflow_dispatch is the GitHub-supported explicit exception; dispatch
    # only this free offline contract workflow on the exact repaired branch.
    try:
        api.call("/actions/workflows/sky-chat-bridge-tests.yml/dispatches",
                 "POST", {"ref": repair_branch})
        result["downstream_ci_dispatch"] = "REQUESTED"
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404, 422):
            result["blockers"].append("DOWNSTREAM_DISPATCH_HTTP_" + str(exc.code))
            result["downstream_ci_dispatch"] = "BLOCKED"
            result["state"] = "DRAFT_SMOKE_REPAIR_CREATED_CI_DISPATCH_BLOCKED"
            return result
        raise
    result["state"] = "DRAFT_SMOKE_REPAIR_CREATED_CI_DISPATCHED_AWAITING_PROOF"
    return result


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    event = os.environ.get("GITHUB_EVENT_NAME", "manual")
    write = os.environ.get("SKY_APPROVED_SAFE_PATCH", "").lower() == "true"
    result = None
    try:
        api = Github(os.environ.get("GITHUB_REPOSITORY", ""),
                     os.environ.get("GH_TOKEN", ""))
        # workflow_run is only for the exact failed free contract CI, current PR head.
        if event == "workflow_run":
            event_file = os.environ.get("GITHUB_EVENT_PATH")
            payload = json.loads(Path(event_file).read_text()) if event_file else {}
            run_info = payload.get("workflow_run", {})
            linked_prs = run_info.get("pull_requests") or []
            # GitHub may return pull_requests=[] for genuine pull_request runs.
            # In that case accept *only* the exact current trusted PR head SHA;
            # run() checks SHA, repository, draft state and branch before writes.
            # Never accept ambiguous or non-target linked PRs.
            linked_pr_identity_ok = (
                not linked_prs
                or (len(linked_prs) == 1 and linked_prs[0].get("number") == TARGET_PR)
            )
            trusted_failure = (
                payload.get("action") == "completed"
                and run_info.get("name") == "Sky Chat Bridge Unit Checks"
                and (run_info.get("repository") or {}).get("full_name") == api.repo
                and (run_info.get("head_repository") or {}).get("full_name") == api.repo
                and run_info.get("event") == "pull_request"
                and run_info.get("conclusion") == "failure"
                and type(run_info.get("run_attempt")) is int
                and run_info["run_attempt"] == 1
                and (run_info.get("head_branch") in (TARGET_BRANCH, SMOKE_BRANCH))
                and str(run_info.get("path") or "").split("@", 1)[0] == ".github/workflows/sky-chat-bridge-tests.yml"
                and bool(run_info.get("head_sha"))
            )
            target_branch = run_info.get("head_branch")
            if target_branch == TARGET_BRANCH:
                trusted_failure = trusted_failure and linked_pr_identity_ok
            elif target_branch == SMOKE_BRANCH:
                trusted_failure = trusted_failure and len(linked_prs) <= 1
            if not trusted_failure:
                result = {"schema": "SKY_GOVERNED_AUTO_REPAIR_V1", "state": "NOT_APPLICABLE",
                          "reason": "UNVERIFIED_TARGET_PR_CI_FAILURE",
                          "production_eligible": False, "automatic_order": False}
            elif target_branch == SMOKE_BRANCH:
                result = run_smoke(api, allow_write=write,
                                   expected_sha=run_info["head_sha"],
                                   linked_prs=linked_prs)
            else:
                result = run(api, allow_write=write, event_name=event,
                             expected_sha=run_info["head_sha"])
        else:
            result = run(api, allow_write=write, event_name=event)
    except Exception as exc:
        result = {"schema": "SKY_GOVERNED_AUTO_REPAIR_V1", "state": "DIAGNOSTIC_FAILURE",
                  "error_type": type(exc).__name__, "error": str(exc)[:150],
                  "production_eligible": False, "automatic_order": False}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if result["state"] == "DIAGNOSTIC_FAILURE":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
