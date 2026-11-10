"""Read-only five-minute Sky engineering health monitor.

No Fugle calls, trades, PR merges, Production changes or automatic CI reruns.
Only GitHub metadata; this is NOT a market-data or scheduled-scan acceptance.
"""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "cr8kj7k7j4-byte/sky-cloud-scanner")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = Path("output/engineering_5m_monitor")
OUT.mkdir(parents=True, exist_ok=True)
RUN_ID = os.getenv("GITHUB_RUN_ID", "LOCAL")
NOW = datetime.now(timezone.utc).isoformat()
WORKFLOWS_SCAN_LIMIT = 35


def api(path):
    url = "https://api.github.com" + path
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN_MISSING")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + TOKEN,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "sky-engineering-readonly-monitor",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f"GITHUB_API_HTTP_{exc.code}") from None
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise RuntimeError("GITHUB_API_UNAVAILABLE") from None
        time.sleep(1 + attempt * 2)


def pr_status(n):
    d = api(f"/repos/{REPO}/pulls/{n}")
    sha = d.get("head", {}).get("sha")
    branch = d.get("head", {}).get("ref")
    query = urllib.parse.urlencode({"branch": branch, "event": "pull_request", "per_page": 70})
    runs = api(f"/repos/{REPO}/actions/runs?{query}").get("workflow_runs", [])
    exact = [
        {"id": r.get("id"), "name": r.get("name"), "status": r.get("status"),
         "conclusion": r.get("conclusion"), "head_sha": r.get("head_sha"),
         "url": r.get("html_url")}
        for r in runs if r.get("head_sha") == sha
    ]
    checks = [r for r in exact if re.search(
        r"Chat Bridge|W3B|Production E2E|Snapshot", r.get("name") or "", re.I
    )]
    failed = [r for r in checks if r["conclusion"] in ("failure", "timed_out", "action_required")]
    pending = [r for r in checks if r["status"] != "completed"]
    selected = (checks or exact)[:12]
    return {
        "number": n,
        "url": d.get("html_url"),
        "state": d.get("state"),
        "draft": bool(d.get("draft")),
        "merged": bool(d.get("merged")),
        "head_sha": sha,
        "updated_at": d.get("updated_at"),
        "relevant_ci": selected,
        "relevant_ci_failed": len(failed),
        "relevant_ci_pending": len(pending),
        "relevant_ci_found": len(checks),
    }


def schedule_audit():
    entries = api(f"/repos/{REPO}/contents/.github/workflows")
    matching = [
        e for e in entries if isinstance(e, dict) and e.get("type") == "file"
        and re.search(r"sky|scan|daytrade|intraday|quick|bridge|snapshot|monitor", e.get("name", ""), re.I)
    ]
    candidates = []
    for entry in matching[:WORKFLOWS_SCAN_LIMIT]:
        name = entry["name"]
        path = urllib.parse.quote(entry["path"], safe="/")
        data = api(f"/repos/{REPO}/contents/{path}")
        try:
            raw = base64.b64decode(data["content"]).decode("utf-8")
        except (KeyError, ValueError, UnicodeDecodeError):
            candidates.append({"file": name, "cron": [], "parse_error": True})
            continue
        crons = re.findall(r"(?m)^\s*-?\s*cron:\s*['\"]?([^'\"\n#]+)", raw)
        candidates.append({"file": name, "cron": [x.strip() for x in crons]})
    from collections import defaultdict
    by_cron = defaultdict(list)
    for item in candidates:
        for cron in item.get("cron", []):
            by_cron[cron].append(item["file"])
    duplicate_cron_candidates = {k: v for k, v in by_cron.items() if len(v) > 1}
    return {
        "repo_workflow_count": len(entries),
        "matched_filenames": len(matching),
        "inspected": len(candidates),
        "truncated": len(matching) > WORKFLOWS_SCAN_LIMIT,
        "candidate_workflows": candidates,
        "same_cron_review_candidates": duplicate_cron_candidates,
        "limitation": "Identical cron does not prove duplicate API calls; manual job-purpose audit required.",
    }


def run():
    result = {
        "schema": "SKY_ENGINEERING_MONITOR_V1",
        "generated_at_utc": NOW,
        "run_id": RUN_ID,
        "run_url": f"https://github.com/{REPO}/actions/runs/{RUN_ID}",
        "source": "GITHUB_REST_METADATA_ONLY",
        "market_data_checked": False,
        "production_changed": False,
        "automatic_order": False,
        "poll_every_minutes": 5,
    }
    try:
        result["pr511"] = pr_status(511)
        result["pr510"] = pr_status(510)
        result["schedule_audit"] = schedule_audit()
        problems = []
        if result["pr511"]["state"] == "open" and result["pr511"]["draft"]:
            problems.append("PR_511_DRAFT_W0_REVIEW_PENDING")
        if result["pr511"]["relevant_ci_failed"]:
            problems.append("PR_511_CI_FAILED_REVIEW_LOGS")
        if result["pr511"]["relevant_ci_pending"]:
            problems.append("PR_511_CI_IN_PROGRESS")
        if result["pr511"]["relevant_ci_found"] == 0:
            problems.append("PR_511_LATEST_HEAD_CI_NOT_FOUND")
        if result["schedule_audit"]["same_cron_review_candidates"]:
            problems.append("SAME_CRON_MANUAL_DUPLICATE_AUDIT_REQUIRED")
        if result["schedule_audit"]["truncated"]:
            problems.append("WORKFLOW_AUDIT_TRUNCATED")
        result["blockers"] = problems
        result["status"] = "ACCEPTANCE_PENDING" if problems or not result["pr511"]["merged"] else "REVIEW_COMPLETE_VERIFY_FINAL_GATES"
        result["next_action"] = (
            "Review PR #511 latest-head evidence, scan artifacts, and W0/P0-G decision; no automatic merge."
            if not result["pr511"]["merged"]
            else "Verify real scheduled scan, data freshness and W0/P0-G record independently."
        )
    except Exception as exc:
        result["status"] = "MONITOR_ERROR"
        result["blockers"] = [str(exc)[:120]]
        result["next_action"] = "Retry next scheduled check; inspect workflow logs if repeated."
    path = OUT / "latest.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# Sky engineering five-minute monitor",
        f"- Checked (UTC): {NOW}",
        f"- Monitor status: **{result['status']}**",
        "- Data source: GitHub metadata only; no Fugle API requests.",
        "- This monitor does not repair code, approve PRs, promote Production or trade.",
    ]
    if "pr511" in result:
        p = result["pr511"]
        md.extend([
            f"- PR #511: {p['state']} / draft={p['draft']} / merged={p['merged']}",
            f"- PR #511 SHA: {p['head_sha']}",
            f"- Relevant CI: {p['relevant_ci_found']} found, {p['relevant_ci_pending']} pending, {p['relevant_ci_failed']} failed",
            f"- Workflow schedule files audited: {result['schedule_audit']['inspected']}/{result['schedule_audit']['matched_filenames']} matching files",
            "- Same-cron workflows require purpose-level audit; identical cron alone is not duplication.",
        ])
    md.extend(["- Blockers: " + (", ".join(result.get("blockers", [])) or "none"), "- Next: " + result["next_action"]])
    content = "\n".join(md) + "\n"
    (OUT / "latest.md").write_text(content, encoding="utf-8")
    print(content)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        Path(summary).write_text(content, encoding="utf-8")
    return 1 if result["status"] == "MONITOR_ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(run())
