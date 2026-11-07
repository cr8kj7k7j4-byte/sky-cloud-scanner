"""Read-only Fugle bulk snapshot vs TWSE/TPEx official universe comparison.

Coverage here means *membership*, NEVER per-symbol executed-price evidence.
A 200 response, lastPrice or lastUpdated is insufficient to authorize trades.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")
MARKETS = {"TSE": "TWSE", "OTC": "TPEx"}


def audit_snapshot(universe, snapshots, asof):
    """Return sanitized, reproducible symbol-coverage diagnostics without prices."""
    result = {"schema": "FUGLE_SNAPSHOT_UNIVERSE_COVERAGE_V1",
              "checked_at_tpe": asof.isoformat(), "status": "INSUFFICIENT_DATA",
              "market_data_gate": "NO_TRADE",
              "trade_time_verified": False, "whole_market_live_certified": False,
              "markets": {}, "warnings": []}
    for market, exchange in MARKETS.items():
        expected = {str(x["symbol"]) for x in universe if x.get("exchange") == exchange}
        payload = snapshots.get(market)
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            result["markets"][market] = {"status": "SOURCE_UNAVAILABLE",
                                         "expected": len(expected), "matched": 0}
            continue
        data = payload["data"]
        codes = [str(x.get("symbol") or "") for x in data if isinstance(x, dict)]
        counts = Counter(code for code in codes if code)
        symbols = set(counts)
        matched = expected & symbols
        outside = symbols - expected
        source_date = str(payload.get("date") or "")
        status = "SNAPSHOT_SYMBOLS_AVAILABLE" if source_date == asof.date().isoformat() else "STALE_SNAPSHOT"
        result["markets"][market] = {
            "status": status, "source_date": source_date,
            "source_time": str(payload.get("time") or ""),
            "expected": len(expected), "records": len(data),
            "unique_symbols": len(symbols), "matched": len(matched),
            "missing": len(expected - matched), "outside_universe": len(outside),
            "duplicate_symbols": sum(n - 1 for n in counts.values() if n > 1),
            "symbol_coverage_pct": round(100 * len(matched) / len(expected), 2) if expected else 0.0,
            "executed_trade_coverage_pct": None,
        }
    result["symbol_coverage_gate"] = "NOT_EVALUABLE"
    if all(result["markets"].get(m, {}).get("status") == "SNAPSHOT_SYMBOLS_AVAILABLE"
           for m in MARKETS) and all(result["markets"][m]["expected"] > 0 for m in MARKETS):
        result["status"] = "BOTH_MARKETS_SYMBOL_SCOPE_OBSERVED"
        if all(result["markets"][m]["symbol_coverage_pct"] >= 95.0
               and result["markets"][m]["duplicate_symbols"] == 0
               for m in MARKETS):
            result["symbol_coverage_gate"] = "PASS_MEMBERSHIP_ONLY"
        else:
            result["symbol_coverage_gate"] = "REVIEW_LOW_COVERAGE_OR_DUPLICATES"
            result["warnings"].append("MEMBERSHIP_COVERAGE_OR_DUPLICATES_BELOW_GATE")
    else:
        result["warnings"].append("NOT_SAME_DAY_OR_UNAVAILABLE: no live-market certification")
    if any(result["markets"][m].get("duplicate_symbols", 0) for m in MARKETS):
        result["warnings"].append("DUPLICATE_SYMBOLS_IN_SNAPSHOT")
    result["warnings"].append("Snapshot membership is not proof of last-executed trades, spreads, fills or alpha.")
    return result


def official_universe_verified(universe, official_status):
    if official_status.get("warnings"):
        return False
    return (
        sum(1 for row in universe if row.get("exchange") == "TWSE") == official_status.get("twse")
        and sum(1 for row in universe if row.get("exchange") == "TPEx") == official_status.get("tpex")
        and int(official_status.get("twse") or 0) > 0
        and int(official_status.get("tpex") or 0) > 0
    )


def main():
    from src.fugle import snapshot_quotes
    from src.official import load_official_universe

    now = datetime.now(TPE)
    universe, official_status = load_official_universe()
    payloads = {}
    errors = {}
    for market in MARKETS:
        try:
            payloads[market] = snapshot_quotes(market)
        except Exception as e:
            errors[market] = type(e).__name__  # Never store API keys or provider response body.
    report = audit_snapshot(universe, payloads, now)
    report["official_counts"] = {"twse": official_status["twse"], "tpex": official_status["tpex"]}
    report["official_warning_count"] = len(official_status.get("warnings") or [])
    report["provider_error_types"] = errors
    if not official_universe_verified(universe, official_status):
        report["symbol_coverage_gate"] = "NOT_EVALUABLE_OFFICIAL_UNIVERSE"
        report["warnings"].append("OFFICIAL_UNIVERSE_UNVERIFIED")
        report["status"] = "INSUFFICIENT_DATA"
        report["whole_market_live_certified"] = False
        report["market_data_gate"] = "NO_TRADE"
    dst = Path("output/provider_readiness/fugle_snapshot_coverage.json")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Sky Fugle snapshot symbol audit:", report["status"])
    for market, row in report["markets"].items():
        print(f"{market}: {row.get('matched',0)}/{row.get('expected',0)}; status={row['status']}; "
              f"symbol_coverage_pct={row.get('symbol_coverage_pct','N/A')}")
    print("IMPORTANT: snapshot symbol coverage is not executed-price live coverage or a trading signal.")


if __name__ == "__main__":
    main()
