"""Sky research-only deterministic repair controller.

No LLM-generated patch, no paid market calls, no Production promotion.
Self-review is a gate, never W0/P0-G approval.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request

REPO = os.getenv("GITHUB_REPOSITORY", "cr8kj7k7j4-byte/sky-cloud-scanner")
TOKEN = os.getenv("GH_TOKEN", "")
BRANCH = "research/fugle-snapshot-diagnostics-20261110"
PR_NUMBER = 511
OUT = Path("output/sky_auto_repair")
SAFE_CI = "Sky Chat Bridge Unit Checks"
EXPECTED_REPAIR_FILE = "research/sky_full_universe_information.py"
MAX_API_CALLS = 26
calls = 0


def api(path, method="GET", payload=None):
    global calls
    calls += 1
    if calls > MAX_API_CALLS:
        raise RuntimeError("GITHUB_API_CALL_BUDGET_EXCEEDED")
    if not TOKEN:
        raise RuntimeError("MISSING_GITHUB_TOKEN")
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        "https://api.github.com/repos/" + REPO + path,
        headers={"Authorization": "Bearer " + TOKEN,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "sky-auto-repair-research",
                 **({"Content-Type": "application/json"} if body else {})},
        data=body, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = response.read()
        return json.loads(raw) if raw else {}


def get_branch_file(path):
    encoded = urllib.parse.quote(path, safe="/")
    resp = api(f"/contents/{encoded}?ref=" + urllib.parse.quote(BRANCH))
    return base64.b64decode(resp["content"]).decode("utf-8"), resp["sha"]


def prepare_safe_patch(code):
    """Exactly one pre-reviewed invariant; no arbitrary edits or generated heuristics."""
    before = '"snapshot_reference_requires_last_trade_time": True,'
    after = '"snapshot_reference_requires_last_trade_time": False,'
    if before not in code:
        return None
    if code.count(before) != 1:
        raise RuntimeError("REPAIR_ANCHOR_NOT_UNIQUE")
    patched = code.replace(before, after)
    compile(patched, EXPECTED_REPAIR_FILE, "exec")
    assert patched.count(after) == code.count(after) + 1
    assert patched.replace(after, before, 1) == code or (
        code.count(after) > 0 and patched.replace(before, after) == patched)
    return patched


def run():
    report = {
        "schema": "SKY_AUTO_REPAIR_V1",
        "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repo": REPO, "pr": PR_NUMBER, "research_only": True,
        "production_eligible": False, "automatic_order": False,
        "paid_api_calls": 0, "actions": [], "blockers": [],
        "self_review": "PENDING", "w0_p0g_approval": False,
    }
    pr = api(f"/pulls/{PR_NUMBER}")
    sha = pr["head"]["sha"]
    report["head_sha"] = sha
    report["pr_state"] = pr.get("state")
    report["pr_draft"] = pr.get("draft")
    if pr.get("state") != "open" or not pr.get("draft") or pr["head"].get("ref") != BRANCH:
        report["blockers"].append("PR_NOT_OPEN_DRAFT_EXPECTED_BRANCH")
        report["self_review"] = "HOLD"
        return report
    runs = api(f"/actions/runs?event=pull_request&branch=" +
               urllib.parse.quote(BRANCH) + "&per_page=100").get("workflow_runs", [])
    newest = {}
    for r in runs:
        if r.get("head_sha") != sha:
            continue
        name = r.get("name")
        if name not in newest or r["id"] > newest[name]["id"]:
            newest[name] = r
    ci = newest.get(SAFE_CI)
    report["ci"] = {k: {"run": v["id"], "status": v.get("status"),
                        "result": v.get("conclusion")} for k, v in newest.items()
                    if k in (SAFE_CI, "Research Freeze Governance",
                             "Sky Governance E2E Validation")}
    if ci and ci.get("status") == "completed" and ci.get("conclusion") in ("failure", "timed_out"):
        if int(ci.get("run_attempt", 1)) == 1:
            try:
                api(f"/actions/runs/{ci['id']}/rerun-failed-jobs", method="POST")
                report["actions"].append("ONE_BOUNDED_NONPAID_CI_RETRY")
            except urllib.error.HTTPError as e:
                report["blockers"].append("CI_RETRY_HTTP_" + str(e.code))
        else:
            report["blockers"].append("CI_REPEAT_FAILURE_HUMAN_REVIEW")
    elif not ci:
        report["blockers"].append("LATEST_HEAD_CONTRACT_CI_MISSING")
    elif ci.get("status") != "completed":
        report["blockers"].append("LATEST_HEAD_CI_PENDING")
    elif ci.get("conclusion") != "success":
        report["blockers"].append("LATEST_HEAD_CI_NOT_GREEN")

    # Safe, deterministic self-repair only. Does not call Fugle.
    original, blob_sha = get_branch_file(EXPECTED_REPAIR_FILE)
    patch = prepare_safe_patch(original)
    if patch:
        if report["actions"] or (ci and ci.get("status") != "completed"):
            report["blockers"].append("SAFE_PATCH_DEFERRED_UNTIL_CI_STABLE")
        else:
            changed = api(f"/contents/{EXPECTED_REPAIR_FILE}", method="PUT", payload={
                "message": "autorepair(research): restore optional Snapshot trade-time contract",
                "content": base64.b64encode(patch.encode()).decode(),
                "sha": blob_sha, "branch": BRANCH})
            report["actions"].append("PATCH_RESEARCH_ONLY_OPTIONAL_SNAPSHOT_TIME")
            report["patch_commit"] = changed.get("commit", {}).get("sha")
            report["blockers"].append("PATCH_REQUIRES_NEW_HEAD_CI_AND_W0_REVIEW")

    try:
        receipt_text, _ = get_branch_file("docs/SKY_SNAPSHOT_INTEGRITY_RESEARCH_LATEST.json")
        receipt = json.loads(receipt_text)
        report["snapshot_receipt_sha"] = receipt.get("head_sha")
        report["snapshot_run"] = receipt.get("run_id")
        twse = (receipt.get("snapshot_integrity") or {}).get("TWSE", {})
        report["missing_twse"] = twse.get("official_symbols_missing_from_snapshot")
        report["missing_twse_list_count"] = len(receipt.get("twse_missing_official_symbols") or [])
        if receipt.get("head_sha") != sha:
            report["blockers"].append("SNAPSHOT_ARTIFACT_NOT_CURRENT_HEAD")
        if report["missing_twse"] and not receipt.get("missing_symbol_classification_verified"):
            report["blockers"].append("TWSE_MISSING_LISTING_REVIEW")
    except (urllib.error.HTTPError, json.JSONDecodeError, UnicodeError, KeyError) as error:
        report["blockers"].append("SNAPSHOT_RECEIPT_UNAVAILABLE_" + type(error).__name__)

    report["blockers"].extend([
        "CANDIDATE_QUOTE_LIVE_TIMESTAMP_ACCEPTANCE_PENDING",
        "CROSS_WORKFLOW_PAID_API_DEDUP_AUDIT_PENDING",
        "W0_P0G_APPROVAL_REQUIRED",
    ])
    report["self_review"] = "HOLD" if report["blockers"] else "PROMOTE_CANDIDATE"
    return report


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        report = run()
    except Exception as error:
        report = {"schema": "SKY_AUTO_REPAIR_V1",
                  "status": "MONITOR_ERROR", "research_only": True,
                  "production_eligible": False, "automatic_order": False,
                  "paid_api_calls": 0, "w0_p0g_approval": False,
                  "self_review": "HOLD",
                  "blockers": [type(error).__name__ + ": " + str(error)[:160]],
                  "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    report.setdefault("status", "RESEARCH_REPAIR_CHECKED")
    (OUT / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text(
            "## Sky Auto-Repair research self-review\n"
            + "- Status: " + report["status"] + "\n"
            + "- Self-review: " + report.get("self_review", "HOLD") + "\n"
            + "- Actions: " + ", ".join(report.get("actions", [])) + "\n"
            + "- Blockers: " + ", ".join(report.get("blockers", [])) + "\n"
            + "- NO paid API / NO Production / NO live orders\n")
    return 1 if report["status"] == "MONITOR_ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
