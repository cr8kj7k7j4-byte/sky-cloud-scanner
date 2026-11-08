"""Bounded read-only weekday audit for the three-model GitHub schedule.

Evidence hierarchy: GitHub schedule event, dispatcher job conclusion, downstream
workflow_dispatch job conclusion, artifacts. Scheduling causality and GCS content
still require separate run logs and immutable receipts.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")
API = "https://api.github.com"
WORKFLOWS = {
    "ledger": "three-model-fugle-private-ledger.yml",
    "markout": "three-model-next-session-markout.yml",
}
DISPATCHER = "three-model-research-daily-dispatch.yml"
SLOTS = (("ledger", 17, 30), ("markout", 18, 30))


def get_json(url):
    if not url.startswith(API + "/repos/"):
        raise ValueError("unapproved_api_url")
    token = os.getenv("GH_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    if not token or not repo:
        raise RuntimeError("missing_github_auth")
    req = Request(url, headers={"Authorization": "Bearer " + token,
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "sky-three-model-evening-health"})
    with urlopen(req, timeout=20) as res:
        return json.load(res)


def runs_for(workflow, event):
    repo = os.environ["GITHUB_REPOSITORY"]
    return get_json(f"{API}/repos/{repo}/actions/workflows/{workflow}"
                    f"/runs?event={event}&per_page=100").get("workflow_runs", [])


def parse_dt(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(TPE)


def classify(runs, start, end, required_event):
    candidates = []
    for r in runs:
        try:
            stamp = parse_dt(r["created_at"])
        except (ValueError, KeyError, TypeError):
            continue
        if r.get("event") == required_event and r.get("head_branch") == "main" and start <= stamp < end:
            candidates.append((stamp, r))
    candidates.sort(key=lambda x: x[0])
    if not candidates:
        return {"status": "MISSING_RUN", "run_id": None, "conclusion": None,
                "evidence": "No matching GitHub run in the specified TPE window"}
    # Use the earliest plausible run; never call a later manual event scheduled.
    r = candidates[0][1]
    status = "SUCCESS" if r.get("status") == "completed" and r.get("conclusion") == "success" else "RUN_NOT_SUCCESSFUL"
    return {"status": status, "run_id": r.get("id"),
            "conclusion": r.get("conclusion"), "created_at": r.get("created_at"),
            "url": r.get("html_url"),
            "evidence": "Run event/time window only; cron identity unverified"}


def assess(now, dispatcher_runs, child_runs, enabled=True):
    local = now.astimezone(TPE)
    day = local.date()
    report = {"date_tpe": day.isoformat(), "checked_at_tpe": local.isoformat(),
              "scope": "research GitHub Actions schedule and downstream dispatch",
              "enabled": enabled, "production_signal": False, "trading_enabled": False,
              "cron_identity_certified": False, "gcs_content_verified": False,
              "slots": [], "status": "UNVERIFIED"}
    if not enabled:
        report["status"] = "DISABLED_BY_CONFIGURATION"
        return report
    if local.weekday() >= 5:
        report["status"] = "WEEKEND_NO_SCHEDULE_EXPECTED"
        return report
    for task, hour, minute in SLOTS:
        start = datetime.combine(day, time(hour, minute), tzinfo=TPE)
        # Separate the 17:30 and 18:30 windows; 75 minute grace for the final slot.
        end = start + timedelta(minutes=55 if task == "ledger" else 75)
        if local < end:
            report["slots"].append({"task": task, "status": "AWAITING_WINDOW_END",
                                    "expected_at_tpe": start.isoformat()})
            continue
        parent = classify(dispatcher_runs, start, end, "schedule")
        # Child workflow_dispatch must follow its expected schedule slot; cannot
        # claim exact parent-child link without an explicit correlation receipt.
        child = classify(child_runs.get(task, []), start, end, "workflow_dispatch")
        status = "RUNS_COMPLETED_UNCORRELATED" if (
            parent["status"] == "SUCCESS" and child["status"] == "SUCCESS"
        ) else "ATTENTION"
        report["slots"].append({"task": task, "expected_at_tpe": start.isoformat(),
                                "dispatcher": parent, "downstream": child, "status": status})
    report["status"] = (
        "RUNS_COMPLETED_UNCORRELATED" if len(report["slots"]) == len(SLOTS)
        and all(x["status"] == "RUNS_COMPLETED_UNCORRELATED" for x in report["slots"])
        else "ATTENTION" if any(x["status"] == "ATTENTION" for x in report["slots"])
        else "AWAITING_WINDOW_END"
    )
    report["note"] = ("Matching successful runs cannot alone prove schedule cron identity, "
                      "parent-child correlation, Fugle completeness, or GCS SHA256 readback.")
    return report


def main():
    enabled = os.getenv("SKY_THREE_MODEL_SCHEDULE_ENABLED", "").lower() == "true"
    now = datetime.now(timezone.utc)
    parent = runs_for(DISPATCHER, "schedule") if enabled else []
    children = {name: runs_for(workflow, "workflow_dispatch") for name, workflow in WORKFLOWS.items()} if enabled else {}
    result = assess(now, parent, children, enabled=enabled)
    out = Path("output/three_model_evening_health")
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (out / "latest.md").open("w", encoding="utf-8") as f:
        f.write("# 三模型晚間排程驗收\n\n")
        f.write(f"台灣日期：{result['date_tpe']}；狀態：{result['status']}\n\n")
        for row in result["slots"]:
            f.write(f"- {row['task']}: {row['status']}; dispatcher="
                    f"{row.get('dispatcher',{}).get('run_id')}; downstream="
                    f"{row.get('downstream',{}).get('run_id')}\n")
        f.write("\n工作流程成功不代表資料完整，也不代表正式交易資格。\n")
    summary = Path(os.getenv("GITHUB_STEP_SUMMARY", ""))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with summary.open("a", encoding="utf-8") as f:
            f.write((out / "latest.md").read_text(encoding="utf-8"))
    print(json.dumps({"status": result["status"],
                      "date_tpe": result["date_tpe"],
                      "slots": len(result["slots"]),
                      "production_signal": False}, ensure_ascii=False))
    if result["status"] == "ATTENTION":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
