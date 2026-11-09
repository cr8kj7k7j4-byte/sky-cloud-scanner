"""Bounded overnight pre-open monitoring. No order placement or risk changes."""
import json
import os
from datetime import datetime, time
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")
END = datetime(2026, 11, 10, 9, 50, tzinfo=TPE)
URL = "https://api.github.com/repos/"


def api(path, body=None, method=None):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(URL + os.environ["GITHUB_REPOSITORY"] + path, data=data,
                  method=method,
                  headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                           "Accept": "application/vnd.github+json",
                           "X-GitHub-Api-Version": "2022-11-28",
                           "User-Agent": "Sky-preopen-watch"})
    with urlopen(req, timeout=25) as res:
        raw = res.read()
        return json.loads(raw) if raw else {}


def is_tuesday_run(run):
    value = run.get("created_at") or ""
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(TPE)
        return when.date().isoformat() == "2026-11-10"
    except ValueError:
        return False


def evaluate(now, getter):
    if now > END:
        return {"status": "EXPIRED", "trading_approved": False}
    result = {"schema": "SKY_PREOPEN_WATCH_V1", "time_tpe": now.isoformat(),
              "trading_approved": False, "retry": "NOT_ELIGIBLE", "workflows": {}}
    for workflow in ("sky-global-premarket.yml", "scan.yml"):
        rows = getter(workflow)
        rows = [x for x in rows if x.get("head_branch") == "main"
                and x.get("event") in ("schedule", "workflow_dispatch")]
        current = [x for x in rows if is_tuesday_run(x)]
        result["workflows"][workflow] = {
            "latest": (rows[0].get("html_url") if rows else None),
            "latest_status": (rows[0].get("conclusion") or rows[0].get("status") if rows else None),
            "target_runs": [{"id": x.get("id"), "event": x.get("event"),
                             "status": x.get("status"), "conclusion": x.get("conclusion")}
                            for x in current[:8]]}
    if now.date().isoformat() == "2026-11-10" and now.time() >= time(8, 20):
        rows = result["workflows"]["sky-global-premarket.yml"]["target_runs"]
        if any(x["conclusion"] == "success" for x in rows):
            result["retry"] = "NO_RETRY_SUCCESS"
        elif any(x["event"] == "workflow_dispatch" for x in rows):
            result["retry"] = "NO_RETRY_ALREADY_DISPATCHED"
        elif any(x["status"] in ("queued", "in_progress", "waiting", "pending") for x in rows):
            result["retry"] = "NO_RETRY_IN_PROGRESS"
        else:
            result["retry"] = "ONE_RETRY_PERMITTED"
    if (now.date().isoformat() == "2026-11-10"
            and now.time() >= time(8, 50)):
        report_runs = result["workflows"]["sky-global-premarket.yml"]["target_runs"]
        if not any(r["conclusion"] == "success" for r in report_runs):
            result["status"] = "PREOPEN_REPORT_FAILED"
    return result


def main():
    now = datetime.now(TPE)
    def runs(workflow):
        return api("/actions/workflows/" + workflow + "/runs?per_page=30").get("workflow_runs", [])
    try:
        status = evaluate(now, runs)
        pre = status.get("workflows", {}).get("sky-global-premarket.yml", {})
        today_runs = pre.get("target_runs") or []
        succeeded = next((x for x in today_runs if x.get("conclusion") == "success"), None)
        if succeeded:
            artifact_data = api("/actions/runs/" + str(succeeded["id"]) + "/artifacts")
            has_report = any(a.get("name", "").startswith("sky-global-premarket-")
                             and not a.get("expired") for a in artifact_data.get("artifacts", []))
            pre["artifact_present"] = has_report
            pre["report_content_verified"] = False
            pre["readiness"] = "REPORT_ARTIFACT_PRESENT_CONTENT_UNVERIFIED" if has_report else "MISSING_REPORT_ARTIFACT"
        if status.get("status") == "EXPIRED":
            api("/actions/workflows/sky-preopen-watch-20261110.yml/disable", method="PUT")
            status["status"] = "DISABLED_AFTER_DEADLINE"
        if status.get("retry") == "ONE_RETRY_PERMITTED":
            api("/actions/workflows/sky-global-premarket.yml/dispatches", {"ref": "main"})
            status["retry"] = "GLOBAL_REPORT_REDISPATCHED_ONCE"
    except Exception as exc:
        status = {"status": "WATCH_ERROR", "error_type": type(exc).__name__,
                  "time_tpe": now.isoformat(), "trading_approved": False}
    path = Path("output/preopen_watch/status.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
        out.write("Sky preopen watch; reports are not trading clearance.\n\n")
        out.write(json.dumps(status, ensure_ascii=False, indent=2))
    print(json.dumps(status, ensure_ascii=False))
    if status.get("status") in ("WATCH_ERROR", "PREOPEN_REPORT_FAILED"):
        raise SystemExit("Preopen readiness warning: see artifact")


if __name__ == "__main__":
    main()
