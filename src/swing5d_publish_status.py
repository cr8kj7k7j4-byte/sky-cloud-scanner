"""Publish a bounded, fail-closed Swing 5D status readable by GitHub connectors."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPORT = Path("output/swing_live/latest_swing5d.json")
STATUS = Path("docs/SKY_SWING5D_LATEST_STATUS.json")
COLUMNS = (
    "股票代碼", "股票名稱", "即時價", "分類", "方向",
    "多方評分", "空方評分", "買進觸發", "最高接受價",
    "停損／失效", "現在動作", "加碼價格", "停利價格",
)


def build_status(payload, run_id, completed_at_utc=None):
    """Never interpret observations or a blocked data gate as trading approval."""
    valid = isinstance(payload, dict)
    preview = payload.get("information_preview_13col") or [] if valid else []
    gate = payload.get("market_data_gate") if valid else None
    passed = bool(
        valid
        and payload.get("operational_full_market_scan") is True
        and (payload.get("live_market_evidence") or {}).get("valid_whole_market_operational") is True
        and payload.get("quote_scope") == "WHOLE_MARKET_EXECUTED_LIVE"
        and gate == "PASS_OPERATIONAL_WHOLE_MARKET_LIVE_RESEARCH_ONLY"
    )
    return {
        "schema": "SKY_SWING5D_CHAT_STATUS_V1",
        "scan_id": str(run_id),
        "run_url": f"https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/{run_id}",
        "completed_at_utc": completed_at_utc or datetime.now(timezone.utc).isoformat(),
        "status": ("REPORT_READY_RESEARCH_ONLY" if passed else
                   "BLOCKED_EXTERNAL_DATA" if valid else "REPORT_MISSING"),
        "data_timestamp": payload.get("generated_at") if valid else None,
        "strategy_status": "RESEARCH_ONLY_HOLD",
        "market_data_gate": gate,
        "operational_full_market_scan": passed,
        "universe_count": payload.get("universe_count") if valid else None,
        "quote_count": payload.get("quote_count") if valid else None,
        "quote_coverage_pct": payload.get("quote_coverage_pct") if valid else None,
        "snapshot_coverage_pct": payload.get("snapshot_coverage_pct") if valid else None,
        "information_count_13col": payload.get("information_count_13col") if valid else 0,
        "information_columns_13col": list(COLUMNS),
        "preview": [{k: row.get(k, "待確認") for k in COLUMNS}
                    for row in preview[:20] if isinstance(row, dict)],
        "unverified_snapshot_warning": payload.get("snapshot_observation_warning") if valid else None,
        "trade_decision": "禁止新進場、未驗證通過",
        "production_eligible": False,
        "artifact_path": "output/swing_live/latest_swing5d.json",
        "note": "Bulk snapshot prices without verified execution timestamps are NOT live prices.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    payload = None
    if REPORT.exists():
        try:
            payload = json.loads(REPORT.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    status = build_status(payload, args.run_id)
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SWING5D_STATUS={status['status']} RUN_ID={args.run_id}")


if __name__ == "__main__":
    main()
