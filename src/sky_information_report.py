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


 
# All requested columns are present, even when the source cannot verify them.
DISPLAY_FIELDS = (
    "股票代碼", "股票名稱", "即時價", "最近已知成交快照（可能延遲）", "資料時間", "資料來源",
    "當日成交量", "融資維持率", "方向", "多方評分", "空方評分",
    "買進觸發", "買進區間", "最高接受價", "停損／失效",
    "目標一", "目標二", "加碼條件", "成本後RR",
    "分類", "現在動作", "模型／驗證狀態",
)


def _first(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = row.get(name)
        if value is not None and value != "":
            return value
    return None


def _fresh_trade_time(value: Any) -> bool:
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            epoch = float(value)
            if epoch > 1e14:
                epoch /= 1_000_000
            elif epoch > 1e11:
                epoch /= 1_000
            observed = datetime.fromtimestamp(epoch, tz=timezone.utc)
        elif isinstance(value, str):
            observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            return False
        if observed.tzinfo is None:
            return False
        age = (datetime.now(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds()
        return -30 <= age <= 120
    except (ValueError, OverflowError, OSError, TypeError):
        return False


def _display_row(row: dict[str, Any], *, full_live: bool) -> dict[str, Any]:
    # Executed last-trade evidence must not be confused with an old closing,
    # opening, bid/ask or reference price.
    status = _first(row, "data_status", "quote_status")
    verified = status in ("VERIFIED_EXECUTED_TRADE", "REALTIME_QUOTE_VERIFIED")
    raw_trade = _first(row, "last_trade_price", "lastPrice", "fugle_close")
    trade_time = _first(row, "last_trade_time", "lastTradeTime", "quote_time")
    price = raw_trade if verified and _fresh_trade_time(trade_time) else None
    symbol = _first(row, "symbol", "stock_id", "code")
    result = {name: None for name in DISPLAY_FIELDS}
    result.update({
        "股票代碼": symbol,
        "股票名稱": _first(row, "name", "stock_name"),
        "即時價": price,
        "最近已知成交快照（可能延遲）": raw_trade if verified else None,
        "資料時間": trade_time,
        "資料來源": _first(row, "source", "quote_source"),
        "當日成交量": _first(row, "trade_volume", "total_volume", "volume") if verified else None,
        "融資維持率": _first(row, "margin_maintenance_ratio") if row.get("margin_ratio_verified") is True else None,
        "方向": _first(row, "direction", "research_direction"),
        "多方評分": _first(row, "bull_score") if row.get("score_inputs_verified") is True else None,
        "空方評分": _first(row, "bear_score") if row.get("score_inputs_verified") is True else None,
        "停損／失效": _first(row, "invalid_reason", "risk_block_reason"),
        "分類": "X",
        "現在動作": "禁止交易",
        "模型／驗證狀態": "未驗證／僅供觀察" if not full_live else "資料符合全市場閘門；交易仍須個別驗證",
    })
    # Never promote source-provided unverified trigger/targets into a
    # synthetic executable order plan. All trading levels remain unknown.
    return result


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
        observed = scan.get("deep_candidates")
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
        "required_display_fields": list(DISPLAY_FIELDS),
        "display_rows": [_display_row(row, full_live=full_live) for row in records],
        "display_missing_value": "待確認（缺少可驗證資料）",
        "observed_candidate_count": len(records),
        "warnings": [
            "研究觀察不等於正式交易訊號；未驗證成交價不可作即時價。",
            "不以收盤價、委買賣價、舊報價補成當日逐筆成交價。",
            "資料不完整仍提供真實已取得的資訊，但不解除 P0-R、A+、成本後 RR 與停損限制。",
        ],
    }



def project_unified_information(payload: dict[str, Any]) -> dict[str, Any]:
    """List actual strategy observations from a composite, without fake live quotes."""
    result = payload.get("result")
    result = result if isinstance(result, dict) else {}
    reports = result.get("reports")
    reports = reports if isinstance(reports, dict) else {}
    observations: list[dict[str, Any]] = []
    strategy_states: dict[str, dict[str, Any]] = {}
    for strategy, raw_report in reports.items():
        report = raw_report if isinstance(raw_report, dict) else {}
        strategy_states[str(strategy)] = {
            key: report.get(key) for key in (
                "available", "data_timestamp", "quote_scope", "source_scope",
                "operational_full_market_scan", "quote_coverage_pct",
                "candidate_count", "research_only", "reason"
            )
        }
        preview = report.get("candidate_preview")
        if not isinstance(preview, list):
            continue
        for candidate in preview:
            if not isinstance(candidate, dict) or not candidate.get("symbol"):
                continue
            safe = {
                "symbol": candidate.get("symbol"),
                "name": candidate.get("name"),
                "direction": candidate.get("direction"),
                "source": report.get("source_scope"),
                # Historical preview price is not equivalent to executed-trade
                # price without a trade time/status for this exact symbol.
                "data_status": "UNVERIFIED_COMPOSITE_PREVIEW",
            }
            observations.append({
                "strategy": str(strategy), **_display_row(safe, full_live=False)
            })
    return {
        "schema": "SKY_INFORMATION_FIRST_UNIFIED_V1",
        "information_available": bool(reports),
        "data_status": "PARTIAL_OR_UNVERIFIED",
        "decision": result.get("decision", "UNKNOWN"),
        "run_id": payload.get("run_id"),
        "generated_at": payload.get("utc_generated_at"),
        "required_display_fields": list(DISPLAY_FIELDS),
        "strategies": strategy_states,
        "display_rows": observations,
        "display_missing_value": "待確認（缺少可驗證資料）",
        "trading_permission": "NO_TRADE_UNLESS_SEPARATELY_AUTHORIZED_BY_P0_R",
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
    result = (
        project_unified_information(payload)
        if isinstance(payload, dict) and isinstance(payload.get("result"), dict)
        else project_information_first(payload)
    )
    result["source_status"] = source_status
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Sky information report:", dest, source_status)


if __name__ == "__main__":
    main()
