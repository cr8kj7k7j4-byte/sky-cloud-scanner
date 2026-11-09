"""Information-first, non-executable reporting for Sky scan artifacts.

This is an additive read-only projection. It never changes scanner admission,
P0-R risk decisions, strategy eligibility, source freshness or order permission.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _safe_count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _safe_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if number == number and number not in (float("inf"), float("-inf")) else None


def project_information_first(scan: dict[str, Any] | None) -> dict[str, Any]:
    """Preserve available evidence even when the full-market trading gate fails.

    Source-supplied symbols are *observations*, never synthesized candidates.
    Research observations are not A+ signals or actionable entry prices.
    """
    scan = scan if isinstance(scan, dict) else {}
    evidence = scan.get("live_market_evidence")
    evidence = evidence if isinstance(evidence, dict) else {}
    full_live = (
        scan.get("operational_full_market_scan") is True
        and evidence.get("valid_whole_market_operational") is True
        and scan.get("quote_scope") == "WHOLE_MARKET_EXECUTED_LIVE"
        and scan.get("market_data_gate") == "PASS_FULL_MARKET_LIVE"
    )
    known = {}
    for key in ("data_timestamp", "generated_at", "generated_at_utc", "quote_scope",
                "quote_coverage_pct", "market_data_gate", "operational_full_market_scan",
                "candidate_count"):
        if key in scan and scan[key] is not None:
            known[key] = scan[key]
    # The source owns these counts. Missing counts must remain unknown, not 0.
    coverage = {
        "twse": _safe_count(scan.get("twse_executed_quote_count")),
        "tpex": _safe_count(scan.get("tpex_executed_quote_count")),
        "universe": _safe_count(scan.get("universe_count")),
        "quote_coverage_pct": _safe_number(scan.get("quote_coverage_pct")),
    }
    # Only structured evidence already present in the artifact is exposed.
    observed = scan.get("candidates")
    if not isinstance(observed, list):
        observed = []
    records = [row for row in observed if isinstance(row, dict)]
    return {
        "schema": "SKY_INFORMATION_FIRST_REPORT_V1",
        "information_available": bool(known or records or evidence),
        "live_full_market_verified": full_live,
        "data_status": "VERIFIED_FULL_LIVE" if full_live else "PARTIAL_OR_UNVERIFIED",
        "trading_permission": "NO_TRADE_UNLESS_SEPARATELY_AUTHORIZED_BY_P0_R",
        "source_scope": scan.get("quote_scope") or "UNKNOWN",
        "coverage": coverage,
        "reported_fields": known,
        "observed_candidate_records": records,
        "observed_candidate_count": len(records),
        "warnings": [
            "研究觀察不等於正式交易訊號；未驗證成交價不可作即時價。",
            "不以收盤價、委買賣價、舊報價補成當日逐筆成交價。",
            "資料不完整仍提供真實已取得的資訊，但不解除 P0-R、A+、成本後 RR 與停損限制。",
        ],
    }


def main() -> None:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Publish non-executable scan observations")
    parser.add_argument("--input", default="output/latest.json")
    parser.add_argument("--output", default="output/information_first.json")
    args = parser.parse_args()
    source = Path(args.input)
    source_status = "REPORT_MISSING"
    payload = None
    if source.is_file():
        try:
            candidate = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(candidate, dict):
                payload = candidate
                source_status = "REPORT_READ"
            else:
                source_status = "REPORT_INVALID_TYPE"
        except (OSError, ValueError):
            source_status = "REPORT_INVALID_JSON"
    result = project_information_first(payload)
    result["source_status"] = source_status
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Sky information report:", dest, source_status)


if __name__ == "__main__":
    main()
