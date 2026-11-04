"""Read-only market-data capability preflight; never changes strategy or trades."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")


def classify_exception(exc):
    """Stable, non-secret error classification for externally gated endpoints."""
    if isinstance(exc, PermissionError):
        return "PLAN_BLOCKED"
    if isinstance(exc, RuntimeError) and "Missing FUGLE_API_KEY" in str(exc):
        return "NO_API_KEY"
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status in (401, 403):
        return "AUTH_OR_PLAN_BLOCKED"
    if status == 429:
        return "RATE_LIMITED"
    return "UNAVAILABLE"


def readiness(probes):
    bulk = [probes.get(f"fugle_bulk_{m}") == "AVAILABLE" for m in ("TSE", "OTC")]
    return {
        "bulk_tse_otc_available": all(bulk),
        "market_wide_executed_trade_certified": False,
        "official_tpex_live_certified": False,
        "status": "PERMISSION_READY_NEEDS_LIVE_COVERAGE"
        if all(bulk) else "BLOCKED_BULK_MARKET_PERMISSION",
        "note": "Bulk API access is necessary but not sufficient. Real trading-day coverage, executed prices, timestamps and exchange-specific validation are still required.",
    }


def check(label, func, probes):
    try:
        payload = func()
        if not isinstance(payload, dict):
            probes[label] = "INVALID_RESPONSE"
        else:
            probes[label] = "AVAILABLE"
        return payload
    except Exception as exc:
        probes[label] = classify_exception(exc)
        return None


def run():
    from src.fugle import get_quote, snapshot_quotes
    from src.official import load_official_universe

    probes = {}
    # Check exact REST API credentials available to the GitHub runner, not
    # a separately connected user's Fugle application permissions.
    for market in ("TSE", "OTC"):
        payload = check(f"fugle_bulk_{market}", lambda m=market: snapshot_quotes(m), probes)
        if payload is not None and not isinstance(payload.get("data"), list):
            probes[f"fugle_bulk_{market}"] = "INVALID_RESPONSE"
    for label, symbol in (("fugle_single_TSE", "2330"), ("fugle_single_OTC", "8089")):
        check(label, lambda s=symbol: get_quote(s), probes)

    try:
        universe, summary = load_official_universe()
        mother_pool = {
            "twse": summary.get("twse"),
            "tpex": summary.get("tpex"),
            "total": len(universe),
            "warnings_count": len(summary.get("warnings", [])),
        }
        probes["official_universe"] = (
            "AVAILABLE" if summary.get("twse", 0) > 0 and summary.get("tpex", 0) > 0
            else "PARTIAL"
        )
    except Exception as exc:
        mother_pool = {"total": 0}
        probes["official_universe"] = classify_exception(exc)

    result = {
        "schema": "SKY_P0OPS_PROVIDER_CAPABILITY_V1",
        "checked_at_tpe": datetime.now(TPE).isoformat(),
        "purpose": "READ_ONLY_CAPABILITY_DIAGNOSIS",
        "probes": probes,
        "official_universe": mother_pool,
        "readiness": readiness(probes),
        "live_scan_executed": False,
        "trading_signal_generated": False,
    }
    path = Path("output/p0ops/provider_capability.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        lines = [
            "## Sky market provider permission preflight",
            f"Status: **{result['readiness']['status']}**",
            f"Mother pool: TWSE={mother_pool.get('twse')} TPEx={mother_pool.get('tpex')}",
            *[f"- {k}: {v}" for k, v in probes.items()],
            "This is **not** a live full-market scan, a strategy validation, or a trading signal.",
        ]
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write("\n".join(lines) + "\n")
    return result


if __name__ == "__main__":
    run()
