"""Publish every available MCR research candidate even when trade execution is blocked.

Never interpret the official after-close margin proxy as intraday or as a
verified maintenance ratio. This reader does NOT use a brokerage credential.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE = Path("research_output/mcr_official_proxy_combined_latest.json")
OUTPUT = Path("output/mcr_observation_latest.json")

def build_report(source: dict | None, observed_at: str, scan: dict | None = None) -> dict:
    scan = scan if isinstance(scan, dict) else {}
    rows = []
    reasons = []
    margin_day = None
    coverage = "NOT_VERIFIED"
    if not isinstance(source, dict):
        reasons.append("MCR_SOURCE_MISSING")
    elif (source.get("data_quality") != "BOTH_MARKETS_PASSED"
          or source.get("coverage") != "TWSE_TPEX_VERIFIED"
          or source.get("mode") != "RESEARCH_PROXY_ONLY"
          or source.get("total") != len(source.get("rows", []))):
        reasons.append("MCR_SOURCE_COVERAGE_OR_SCHEMA_UNVERIFIED")
    else:
        margin_day = source.get("margin_data_date")
        coverage = source.get("coverage")
        if not isinstance(margin_day, str) or not margin_day:
            reasons.append("MCR_SOURCE_DATE_MISSING")
        else:
            for item in source["rows"]:
                if not isinstance(item, dict) or item.get("margin_data_date") != margin_day:
                    reasons.append("MCR_ROW_DATE_MISMATCH")
                    rows = []
                    break
                row = dict(item)
                # These are financing-balance proxies, never executable candidates.
                row["trade_eligible"] = False
                row["action"] = "觀察"
                row["research_status"] = "RESEARCH_PROXY_ONLY"
                row["quote_price"] = None
                row["quote_timestamp"] = None
                row["quote_status"] = "NOT_JOINED_TO_VERIFIED_LIVE_QUOTE"
                row["margin_maintenance_pct"] = None
                row["maintenance_below_130_verified"] = False
                rows.append(row)
    live_verified = (
        scan.get("operational_full_market_scan") is True
        and scan.get("market_data_gate") == "PASS_FULL_MARKET_LIVE"
        and (scan.get("live_market_evidence") or {}).get("valid_whole_market_operational") is True
    )
    if not live_verified:
        reasons.append("REALTIME_FULL_MARKET_QUOTE_NOT_VERIFIED")
    reasons.append("MCR_INTRADAY_PRICE_JOIN_NOT_IMPLEMENTED")
    reasons.append("MARGIN_MAINTENANCE_130_NOT_VERIFIED")
    return {
        "schema": "SKY_MCR_OBSERVATION_V1",
        "generated_at": observed_at,
        "financing_source_date": margin_day,
        "source_coverage": coverage,
        "candidate_count": len(rows),
        "market_counts": {
            "TWSE": sum(r.get("exchange") == "TWSE" for r in rows),
            "TPEx": sum(r.get("exchange") == "TPEx" for r in rows),
        },
        "scan_live_gate_verified": live_verified,
        "quote_join_status": "NOT_AVAILABLE",
        "status": "RESEARCH_ONLY_NO_NEW_ENTRY",
        "trade_eligible": False,
        "headline": "🔴 禁止新進場｜仍提供全部可核對融資研究觀察，交易由使用者自行判斷",
        "reasons": reasons,
        "rows": rows,
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--scan", type=Path, default=Path("output/latest.json"))
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    def load(path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
    report = build_report(
        load(args.source),
        datetime.now(ZoneInfo("Asia/Taipei")).isoformat(),
        load(args.scan),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("MCR_RESEARCH_OBSERVATION", report["candidate_count"], report["financing_source_date"], report["reasons"])

if __name__ == "__main__":
    main()
