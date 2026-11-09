"""Repeated paid-Fugle intraday scanner preflight (no trading approval).

Pre-open freshness is UNKNOWN until the actual exchange opens. Distinguish
source/API readiness and report-code readiness from execution/strategy gates.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")
REQUIRED_SCANNER_OUTPUTS = (
    "output/sky_quickscan_information/full_universe.json",
    "output/sky_quickscan_information/latest_13col.md",
    "output/sky_quickscan_information/latest_13col.json",
)
MIN_PROVIDER_SNAPSHOT_ROWS = 500


def evaluate(diagnostics, *, now=None):
    now = now or datetime.now(TPE)
    mis = diagnostics.get("mis_sample") or {}
    markets = {m: diagnostics.get("fugle_snapshot_" + m) or {} for m in ("TSE", "OTC")}
    checks = {}
    checks["NO_FREE_QUOTES"] = mis.get("status") == "SKIPPED_FUGLE_ONLY" and mis.get("requested") == 0
    for market, data in markets.items():
        checks["FUGLE_SNAPSHOT_" + market] = (
            data.get("ok") is True and isinstance(data.get("count"), int)
            and data.get("count") >= MIN_PROVIDER_SNAPSHOT_ROWS
        )
    # Individual API read permission can be verified pre-open without pretending
    # a historical lastTrade is a fresh execution.
    for key in ("fugle_quote_2330", "fugle_quote_8089_otc"):
        data = diagnostics.get(key) or {}
        checks["INDIVIDUAL_" + key] = data.get("api_accessible") is True
    passed = all(checks.values())
    return {
        "schema": "SKY_DAYTRADE_PREOPEN_READINESS_V1",
        "checked_at_tpe": now.isoformat(),
        "market_data_policy": "FUGLE_PAID_ONLY",
        "provider_and_permission_checks": checks,
        "provider_data_dates": {market: markets[market].get("date") for market in markets},
        "provider_snapshot_counts": {market: markets[market].get("count") for market in markets},
        "api_readiness": "PASS" if passed else "BLOCKED",
        "execution_freshness": "NOT_TESTABLE_PREOPEN",
        "strategy_levels": "NOT_VERIFIED",
        "production_trade_eligible": False,
        "action": "禁止交易",
        "expected_scanner_artifacts": list(REQUIRED_SCANNER_OUTPUTS),
        "note": "Preopen permission checks only. Do not upgrade to live execution proof.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnostics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    opts = parser.parse_args()
    diagnostics = json.loads(opts.diagnostics.read_text(encoding="utf-8"))
    report = evaluate(diagnostics)
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["api_readiness"] != "PASS":
        raise SystemExit("FUGLE_PREOPEN_API_READINESS_BLOCKED")


if __name__ == "__main__":
    main()
