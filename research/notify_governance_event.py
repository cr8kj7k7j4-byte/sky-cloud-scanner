from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.notifier import send_telegram


def _load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _pct(value):
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "N/A"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=("w4", "p0r", "w6", "failure"))
    ap.add_argument("--input")
    ap.add_argument("--workflow")
    ap.add_argument("--run-url")
    ap.add_argument("--previous-input")
    args = ap.parse_args()

    if args.kind == "failure":
        workflow = args.workflow or "Sky workflow"
        url = args.run_url or ""
        send_telegram(
            f"🔴 Sky 系統告警｜{workflow}\n"
            f"GitHub Actions 執行失敗，請檢查 workflow log。\n{url}"
        )
        return

    current = _load(args.input) if args.input else {}
    previous = _load(args.previous_input) if args.previous_input else {}

    if args.kind == "w4":
        stage = str(current.get("stage") or "")
        prev_stage = str(previous.get("stage") or "")
        if stage not in {"SAMPLE_READY", "GOVERNANCE_REVIEW_READY"}:
            return
        if stage == prev_stage:
            return
        s = dict(current.get("summary") or {})
        send_telegram(
            "🟢 Sky W4 證據里程碑\n"
            f"狀態：{stage}\n"
            f"樣本：{s.get('samples', 0)}\n"
            f"交易日：{s.get('trading_days', 0)}\n"
            f"Regime：{s.get('regime_count', 0)}\n"
            f"Outcome 完整率：{_pct(s.get('outcome_complete_ratio', 0))}\n"
            f"單一股票最高占比：{_pct(s.get('top_symbol_share', 0))}\n"
            "這是證據成熟度，不代表獲利機率或實盤授權。"
        )
        return

    if args.kind == "p0r":
        status = str(current.get("status") or "")
        prev_status = str(previous.get("status") or "")
        if status != "READY_FOR_P0R_REVIEW" or status == prev_status:
            return
        w4 = dict(current.get("w4") or {})
        send_telegram(
            "🟢 Sky P0-R 風控里程碑\n"
            "狀態：READY_FOR_P0R_REVIEW\n"
            f"W4樣本：{w4.get('samples', 0)}\n"
            f"交易日：{w4.get('trading_days', 0)}\n"
            f"Outcome完整率：{_pct(w4.get('outcome_complete_ratio', 0))}\n"
            "僅代表可進入風控審查，不代表可實盤。"
        )
        return

    if args.kind == "w6":
        status = str(current.get("status_w6") or "")
        prev_status = str(previous.get("status_w6") or "")
        if status != "EXECUTION_CANDIDATE" or status == prev_status:
            return
        send_telegram(
            "🟢 Sky W6 Execution 里程碑\n"
            "狀態：EXECUTION_CANDIDATE\n"
            "已形成可送後續治理審查的 execution evidence。\n"
            "此狀態不代表方向型 Alpha，也不代表實盤授權。"
        )


if __name__ == "__main__":
    main()
