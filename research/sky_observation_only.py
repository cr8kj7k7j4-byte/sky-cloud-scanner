"""Read-only user information report from a completed Sky scan artifact.

This does not fetch live quotes, certify coverage, train AI, or change any
production gate. It keeps available observations visible on a blocked scan.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

def build_report(scan):
    if not isinstance(scan, dict):
        raise ValueError("scan must be a JSON object")
    gate = scan.get("market_data_gate") or "UNKNOWN"
    verified = (
        scan.get("operational_full_market_scan") is True
        and scan.get("full_market_scan") is True
        and gate == "PASS_FULL_MARKET_LIVE"
    )
    # Do not turn a historical/partial source into a full-market claim.
    observations = []
    for group in ("top100", "deep", "deep_rejected", "deep_unverified"):
        rows = scan.get(group)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            observations.append({
                "group": group,
                "symbol": row.get("symbol"),
                "name": row.get("name"),
                "price": row.get("price", row.get("last_price")),
                "quote_time": row.get("last_trade_time", row.get("quote_time")),
                "direction": "UNVERIFIED_RESEARCH_OBSERVATION",
                "action": "觀察",
                "trade_eligible": False,
            })
    return {
        "schema": "SKY_OBSERVATION_ONLY_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_scan_time": scan.get("run_time"),
        "source": "existing Sky scan JSON; not a new market query",
        "data_gate": gate,
        "market_data_verified": verified,
        "full_market_prediction_verified": False,
        "trade_eligible": False,
        "conclusion": "🔴 禁止新進場、未驗證通過",
        "note": "資訊供自行判斷；部分行情、研究方向與模型分數不是已校準隔日漲跌機率。缺少資料時保留空值，不補造。",
        "quote_coverage_pct": scan.get("quote_coverage_pct"),
        "universe_count": scan.get("universe_count"),
        "live_market_evidence": scan.get("live_market_evidence"),
        "source_health": scan.get("source_health"),
        "warnings": scan.get("warnings", []),
        "observations": observations,
        "observation_count": len(observations),
        "no_observation_reason": (
            None if observations else "來源掃描沒有保留候選逐檔資料；不能從彙總數據重建個股名單。"
        ),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="output/latest.json")
    parser.add_argument("--output", default="output/observation_only.json")
    args = parser.parse_args()
    report = build_report(json.loads(Path(args.input).read_text(encoding="utf-8")))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(path), "observation_count": report["observation_count"],
                      "conclusion": report["conclusion"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
