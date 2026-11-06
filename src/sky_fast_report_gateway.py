"""Read-only, low-latency Sky report gateway. No market downloads, no orders.

Uses already-published GitHub status snapshots; never calls an expensive scan.
Only a verified same-session quote can support an actionable realtime result.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")
STATUS_FILES = {
    "Sky 系統快報": "docs/SKY_UNIFIED_LATEST_SYSTEM_HEALTH.json",
    "Sky 全市場快報": "docs/SKY_UNIFIED_LATEST_ALL_MARKET.json",
    "Sky 模型驗證快報": "docs/SKY_UNIFIED_LATEST_MODEL_VALIDATION.json",
    "Sky 證據快報": "docs/SKY_EXTERNAL_LATEST_STATUS.json",
}
ALIAS = {
    "Sky 高速狀態": "Sky 系統快報",
    "Sky 高速全市場": "Sky 全市場快報",
    "Sky 多空最佳機會掃描": "Sky 多空研究快報",
}
MAX_REPORT_AGE = timedelta(minutes=20)

def _timestamp(payload):
    for key in ("published_at_utc", "generated_at_utc", "utc_generated_at"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                continue
    return None

def read_fast_report(command, root=".", now=None):
    """Snapshot status only. Does not authorize new entries or short selling."""
    now = now or datetime.now(TZ)
    command = ALIAS.get(command.strip(), command.strip())
    base = {
        "schema": "SKY_FAST_READ_ONLY_V1",
        "command": command,
        "observed_at_taipei": now.isoformat(),
        "no_new_scan": True,
        "auto_orders_enabled": False,
        "trade_allowed": False,
        "action": "等待",
        "entry": None, "short_entry": None, "stop": None,
        "long_score": None, "short_score": None, "rr_after_cost": None,
        "report_fresh_for_realtime": False,
    }
    if command == "Sky 多空研究快報":
        base.update({
            "state": "RESEARCH_ONLY",
            "reason": "Bidirectional PR #270 is not merged or runtime-verified; short eligibility and after-cost edge unverified.",
            "source": "https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/270",
            "action": "禁止交易",
        })
        return base
    relative_path = STATUS_FILES.get(command)
    if not relative_path:
        base.update({"state": "UNKNOWN_COMMAND", "reason": "Unsupported fast-report command"})
        return base
    base["source_path"] = relative_path
    path = Path(root) / relative_path
    if not path.is_file():
        base.update({"state": "REPORT_MISSING", "reason": "Published report not present; do not infer current market"})
        return base
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Report root is not a JSON object")
    except (OSError, ValueError) as exc:
        base.update({"state": "REPORT_INVALID", "reason": type(exc).__name__})
        return base
    ts = _timestamp(data)
    age = (now - ts.astimezone(TZ)) if ts is not None and ts.tzinfo else None
    age_valid = age is not None and timedelta(0) <= age <= MAX_REPORT_AGE
    current_session = now.weekday() < 5 and time(9, 0) <= now.time() <= time(13, 30)
    same_session = ts is not None and ts.tzinfo is not None and ts.astimezone(TZ).date() == now.date()
    base.update({
        "source_timestamp": ts.isoformat() if ts is not None else None,
        "report_age_seconds": round(age.total_seconds()) if age is not None else None,
        "report_fresh": bool(age_valid and current_session and same_session),
        "report_fresh_for_realtime": False,
        "published_decision": (data.get("decision") or (data.get("w4_dashboard") or {}).get("stage")),
        "published_step_outcome": data.get("scan_step_outcome"),
        "published_run_url": data.get("run_url"),
        "state": "REPORT_AVAILABLE_HISTORICAL_STATUS",
        "reason": "Status artifact, not a validated live actionable trade snapshot",
        "action": "觀察",
    })
    # A successful GitHub job does not certify realtime quote coverage.
    return base

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", required=True, choices=list(STATUS_FILES) + list(ALIAS))
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="output/fast_reports/latest.json")
    args = parser.parse_args()
    result = read_fast_report(args.command, root=args.root)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
