"""Read-only Sky postmarket E2E acceptance; never certifies trading eligibility."""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = os.environ.get("GITHUB_REPOSITORY", "cr8kj7k7j4-byte/sky-cloud-scanner")
TOKEN = os.environ.get("GH_TOKEN", "")
BASE = "https://api.github.com/repos/" + REPO
WORKFLOWS = {
    "當沖掃描程序": "sky-chat-bridge.yml",
    "盤後波段程序": "swing-postmarket-research.yml",
    "六模型研究訊號程序": "sky-research-signal-evidence.yml",
    "排程健康程序": "schedule-health-audit.yml",
}
COLUMNS = ("股票代碼", "股票名稱", "即時價", "分類", "方向",
           "多方評分", "空方評分", "買進觸發", "最高接受價",
           "停損／失效", "現在動作", "加碼價格", "停利價格")


def api(path):
    req = Request(BASE + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "sky-postmarket-acceptance",
        **({"Authorization": "Bearer " + TOKEN} if TOKEN else {}),
    })
    try:
        with urlopen(req, timeout=20) as response:
            return json.load(response), None
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        return None, type(exc).__name__


def workflow_state(runs, error=None):
    if error:
        return "NOT_VERIFIED"
    if not isinstance(runs, list) or not runs:
        return "NOT_VERIFIED"
    run = next((v for v in runs if v.get("status") == "completed"), None)
    if not run:
        return "NOT_VERIFIED"
    if run.get("conclusion") != "success":
        return "FAIL"
    return "PROCESS_PASS"


def data_checks(status):
    if not isinstance(status, dict):
        return {"掃描資料": "NOT_VERIFIED", "13欄報告": "NOT_VERIFIED",
                "有效成交驗證": "NOT_VERIFIED", "正式交易資格": "NOT_VERIFIED"}
    count = status.get("universe_count")
    rows = status.get("row_count")
    preview = status.get("preview")
    report_ok = isinstance(preview, list) and all(
        isinstance(row, dict) and all(column in row for column in COLUMNS)
        for row in preview
    ) and rows == count and isinstance(rows, int) and rows > 0
    observed = status.get("observed_price_count")
    fresh = status.get("fresh_executed_count")
    return {
        "掃描資料": "OBSERVED_ONLY" if isinstance(observed, int) and observed > 0 else "NOT_VERIFIED",
        "13欄報告": "PREVIEW_PASS_FULL_ARTIFACT_NOT_VERIFIED" if report_ok else "NOT_VERIFIED",
        "有效成交驗證": "NOT_VERIFIED" if not isinstance(fresh, int) else (
            "ZERO_VERIFIED" if fresh == 0 else "PARTIAL_VERIFICATION_ONLY"
        ),
        "正式交易資格": "BLOCKED" if status.get("production_eligible") is False
                    else "NOT_VERIFIED",
    }


def overall(checks):
    # No PASS unless actual mobile readback, data-quality and governance evidence exist.
    if any(v == "FAIL" for v in checks.values()):
        return "FAIL"
    return "NOT_VERIFIED"


def main():
    now = datetime.now(timezone.utc)
    out = Path("output/postmarket_acceptance")
    out.mkdir(parents=True, exist_ok=True)
    findings = {}
    evidence = {}
    for label, workflow in WORKFLOWS.items():
        payload, error = api("/actions/workflows/" + workflow + "/runs?per_page=10")
        runs = (payload or {}).get("workflow_runs", [])
        findings[label] = workflow_state(runs, error)
        evidence[label] = {
            "workflow": workflow, "error": error,
            "latest_completed": next(({
                "id": x.get("id"), "created_at": x.get("created_at"),
                "conclusion": x.get("conclusion"), "url": x.get("html_url")
            } for x in runs if x.get("status") == "completed"), None)
        }
    payload, error = api("/contents/docs/SKY_CHAT_LATEST_STATUS.json")
    status = None
    if isinstance(payload, dict) and payload.get("content"):
        try:
            status = json.loads(base64.b64decode(payload["content"]).decode("utf-8"))
        except (ValueError, UnicodeError, TypeError):
            pass
    findings.update(data_checks(status))
    evidence["scan_report"] = {
        "error": error, "scan_id": (status or {}).get("scan_id"),
        "data_timestamp": (status or {}).get("data_timestamp"),
        "universe_count": (status or {}).get("universe_count"),
        "row_count": (status or {}).get("row_count"),
        "observed_price_count": (status or {}).get("observed_price_count"),
        "fresh_executed_count": (status or {}).get("fresh_executed_count"),
        "by_exchange": (status or {}).get("by_exchange"),
        "source": (status or {}).get("source"),
        "run_url": (status or {}).get("run_url"),
    }
    # Snapshot status is never proof of today's official close or mobile delivery.
    findings["當日收盤價與成交量"] = "NOT_VERIFIED"
    findings["ChatGPT本次指令讀回"] = "NOT_VERIFIED"
    findings["六模型入帳與結果追蹤"] = "NOT_VERIFIED"
    findings["即時盤中驗收"] = "NOT_VERIFIED"
    report = {
        "schema": "SKY_POSTMARKET_E2E_ACCEPTANCE_V1",
        "checked_at_utc": now.isoformat(),
        "repository": REPO, "read_only": True, "automatic_order": False,
        "production_promotion": False,
        "overall": overall(findings), "checks": findings, "evidence": evidence,
        "scope": "GitHub run metadata + sanitized scan status; no direct Fugle live session",
        "warnings": ["PROCESS_PASS is not data/model/trading PASS",
                     "13-column preview does not establish full-artifact integrity",
                     "production eligibility remains governed by P0-G"],
    }
    (out / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = ["# Sky 收盤後全系統驗收", "",
          "整體：" + report["overall"], "查核時間 (UTC)：" + report["checked_at_utc"], "",
          "| 項目 | 結果 |", "|---|---|"]
    md += ["| " + key + " | " + value + " |" for key, value in findings.items()]
    md += ["", "本報告僅供唯讀驗收；不得據此升級 Production 或下單。"]
    (out / "latest.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")
    print(json.dumps({"overall": report["overall"], "checks": findings}, ensure_ascii=False))


if __name__ == "__main__":
    main()
