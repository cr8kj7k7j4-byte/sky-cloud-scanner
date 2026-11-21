"""On-demand read-only ChatGPT bridge running inside GitHub Actions.

Only research observations are produced; no trade orders or model promotion.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from research.sky_snapshot_candidates import screen as screen_stage1
from src.sky_stage2_candidate_quotes import verify as verify_stage2
from src.sky_v14_ticker_candles_probe import run as probe_v14_candles
from research.sky_candidate_e2e_chain import write as write_candidate_chain
from src.sky_scan_readback import canonical_command, validate_scan_readback

REQUEST = Path("scan_requests/chat/latest.json")
OUTPUT = Path("output/chat_bridge")
COLUMNS = ("股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分",
           "空方評分", "買進觸發", "最高接受價", "停損／失效",
           "現在動作", "加碼價格", "停利價格")


def validate_request(payload):
    if not isinstance(payload, dict):
        raise ValueError("UNSUPPORTED_COMMAND")
    canonical_command(payload.get("command"))  # All five aliases share this existing runner.
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or not (8 <= len(request_id) <= 80):
        raise ValueError("INVALID_REQUEST_ID")
    if not all(c.isascii() and (c.isalnum() or c in "-_") for c in request_id):
        raise ValueError("UNSAFE_REQUEST_ID")
    if payload.get("read_only_no_orders") is not True:
        raise ValueError("ORDER_POLICY_REQUIRED")
    return request_id


def validate_report(report):
    if report.get("schema") != "SKY_DAYTRADE_13COL_RESEARCH_V2":
        raise ValueError("INVALID_REPORT_SCHEMA")
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != report.get("row_count"):
        raise ValueError("INCOMPLETE_ROWS")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or any(k not in row for k in COLUMNS):
            raise ValueError("MISSING_13_COLUMNS")
        symbol = str(row.get("股票代碼") or "")
        if not symbol or symbol in seen:
            raise ValueError("DUPLICATE_OR_MISSING_SYMBOL")
        seen.add(symbol)
        if row.get("現在動作") in ("買進", "加碼"):
            raise ValueError("RESEARCH_ENTRY_NOT_ALLOWED")
        if row.get("正式交易資格") is not False:
            raise ValueError("ROW_PRODUCTION_ELIGIBILITY_NOT_FALSE")
    if report.get("universe_count") != len(rows):
        raise ValueError("UNIVERSE_REPORT_COUNT_MISMATCH")
    if report.get("production_eligible") is not False:
        raise ValueError("RESEARCH_CANNOT_AUTOPROMOTE")
    return rows



def diagnose_five_minute_path(stage1, stage2, stage3):
    """Explain why the bounded 5m probe did not run; never trigger a paid call."""
    stage1, stage2, stage3 = stage1 or {}, stage2 or {}, stage3 or {}
    exclusions = stage1.get("excluded_reasons") or {}
    candidates = stage1.get("candidate_count", 0)
    attempts = stage2.get("attempted_count", 0)
    verified = stage2.get("verified_executed_count", 0)
    candle_attempts = stage3.get("attempted_api_requests", 0)
    samples = stage3.get("samples") or []
    if not isinstance(exclusions, dict):
        exclusions = {}
    if candidates == 0:
        reason = ("NON_TRADING_SESSION" if exclusions.get("NON_TRADING_WEEKEND", 0) or
                  exclusions.get("NON_TRADING_HOLIDAY", 0) else "NO_STAGE1_CANDIDATES")
    elif attempts == 0:
        reason = "STAGE2_NO_QUOTE_REQUESTS"
    elif verified == 0:
        reason = ("STAGE2_RATE_LIMITED" if stage2.get("rate_limited_count", 0)
                  else "STAGE2_NO_VERIFIED_EXECUTIONS")
    elif candle_attempts == 0:
        reason = "NO_STAGE2_CANDIDATES_PASSED_5M_GATES"
    elif stage3.get("rate_limited"):
        reason = "FIVE_MINUTE_RATE_LIMITED"
    elif any(s.get("status") in ("PLAN_RESTRICTED", "HTTP_ERROR", "SOURCE_ERROR", "INVALID_PROVIDER_PAYLOAD")
             for s in samples if isinstance(s, dict)):
        reason = "FIVE_MINUTE_PROVIDER_ERROR"
    elif any(s.get("valid_today_five_min_bars", 0) > 0 for s in samples if isinstance(s, dict)):
        reason = "FIVE_MINUTE_OBSERVED_RESEARCH_ONLY"
    else:
        reason = "FIVE_MINUTE_DATA_INCOMPLETE"
    return {
        "reason_code": reason,
        "stage1_candidates": candidates,
        "stage1_exclusion_reasons": exclusions,
        "stage2_quote_requests": attempts,
        "stage2_verified_executions": verified,
        "five_minute_api_requests": candle_attempts,
        "five_minute_samples": len(samples),
        "provider_statuses": [s.get("status") for s in samples if isinstance(s, dict)],
        "production_eligible": False,
        "automatic_order": False,
    }



def make_status(request_id, report=None, error=None, observation=None, stage1=None, stage2=None, stage3=None, stage4=None):
    observation = observation or {}
    observed_count = observation.get("observed_price_count", 0)
    exchange_detail = observation.get("by_exchange") or {}
    stage1 = stage1 or {}
    stage2 = stage2 or {}
    stage3 = stage3 or {}
    stage4 = stage4 or {}
    run_id = os.getenv("GITHUB_RUN_ID") or "LOCAL"
    repo = os.getenv("GITHUB_REPOSITORY") or ""
    rows = validate_report(report) if report is not None else []
    # Present ranked observations rather than the first eight listing symbols.
    # This is an information-only preview, never an A+ candidate list.
    by_symbol = {str(r["股票代碼"]): r for r in rows}
    ranked = observation.get("ranked_observations") or []
    preview = []
    for item in ranked:
        symbol = str(item.get("symbol") or "") if isinstance(item, dict) else ""
        if symbol in by_symbol and by_symbol[symbol] not in preview:
            preview.append(by_symbol[symbol])
        if len(preview) >= 8:
            break
    if not preview:
        preview = rows[:8]
    by_market = observation.get("by_exchange") or {}
    snapshot_errors = observation.get("snapshot_errors") or {}
    source_missing = bool(snapshot_errors) or any(
        (by_market.get(market) or {}).get("snapshot_rows", 0) == 0
        for market in ("TWSE", "TPEx")
    )
    report_status = ("DATA_BLOCKED_SOURCE_FAILURE" if source_missing else
                     "REPORT_READY_RESEARCH_ONLY" if observed_count > 0 else
                     "DATA_BLOCKED_NO_OBSERVATIONS")
    return {
        "schema": "SKY_CHAT_SCAN_STATUS_V1",
        "request_id": request_id, "scan_id": run_id,
        "head_sha": os.getenv("GITHUB_SHA"),
        "run_url": f"https://github.com/{repo}/actions/runs/{run_id}" if repo else None,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": report_status if report is not None else "FAILED",
        "data_timestamp": report.get("checked_at_tpe") if report else None,
        "source": "FUGLE_PAID_SNAPSHOT" if observed_count > 0 else None,
        "universe_count": report.get("universe_count") if report else None,
        "row_count": len(rows), "preview": preview,
        "observed_price_count": observed_count,
        "fresh_executed_count": observation.get("fresh_executed_count", 0),
        "by_exchange": exchange_detail,
        "stage1_candidate_count": stage1.get("candidate_count", 0),
        "stage2_attempted_count": stage2.get("attempted_count", 0),
        "stage2_verified_executed_count": stage2.get("verified_executed_count", 0),
        "stage2_rate_limited_count": stage2.get("rate_limited_count", 0),
        "stage2_bounded_operational_probe_pass": stage2.get("operational_bounded_probe_pass", False),
        "stage2_elapsed_seconds": stage2.get("elapsed_seconds"),
        "stage2_max_plan_quota_inferred": False,
        "five_minute_diagnostic": diagnose_five_minute_path(stage1, stage2, stage3),
        "v14_ticker_5m_attempted_api_requests": stage3.get("attempted_api_requests", 0),
        "v14_ticker_5m_samples": (stage3.get("samples") or [])[:2],
        "v14_ticker_5m_artifact": "output/sky_quickscan_information/v14_ticker_5m_evidence.json" if stage3 else None,
        "v14_full_rule_validation_complete": False,
        "candidate_chain_artifact": "output/sky_quickscan_information/candidate_e2e_chain.json" if stage4 else None,
        "candidate_chain_stage2_verified": stage4.get("stage2_quote_verified_count", 0),
        "candidate_chain_5m_observed": stage4.get("stage3_five_minute_observed_count", 0),
        "candidate_chain_vwap_certified": stage4.get("vwap_certified_count", 0),
        "broker_account_required_for_research": False,
        "research_mode": "BROKERLESS_RESEARCH_ONLY",
        "stage2_v14_canonical_audit_invoked": sum(bool(x.get("canonical_v14_p0c_audit")) for x in (stage2.get("results") or [])),
        "stage2_quote_preview": (stage2.get("results") or [])[:6],
        "stage2_artifact": "output/sky_quickscan_information/stage2_quote_evidence.json" if stage2 else None,
        "stage2_rate_limit_plan_verified": False,
        "stage1_by_exchange": stage1.get("by_exchange") or {},
        "stage1_exclusion_reasons": stage1.get("excluded_reasons") or {},
        "stage1_price_limit_exclusive_twd": stage1.get("max_price_exclusive_twd", 100),
        "stage1_candidate_preview": (stage1.get("candidates") or [])[:20],
        "stage1_candidate_artifact": "output/sky_quickscan_information/stage1_candidates.json" if stage1 else None,
        "snapshot_errors": snapshot_errors,
        "observed_price_coverage_pct": round(100 * observed_count / len(rows), 2) if rows else 0.0,
        "fresh_executed_coverage_pct": round(
            100 * observation.get("fresh_executed_count", 0) / len(rows), 2) if rows else 0.0,
        # Explicitly separate an operational report from a verified live strategy.
        # A weekend/previous-session reference price cannot certify executed trades.
        "mobile_research_notice": ("研究報告可讀；五分鐘K棒未驗證：" + diagnose_five_minute_path(stage1, stage2, stage3)["reason_code"] if report is not None else "研究快掃失敗；禁止交易"),
        "research_operational_status": report_status if report is not None else "FAILED",
        "live_strategy_status": "HOLD_INSUFFICIENT_DATA",
        "live_strategy_evidence": {
            "executed_trade_verified_count": observation.get("fresh_executed_count", 0),
            "stage2_verified_executed_count": stage2.get("verified_executed_count", 0),
            "five_minute_observed_count": stage4.get("stage3_five_minute_observed_count", 0),
            "vwap_certified_count": stage4.get("vwap_certified_count", 0),
            "full_rule_validation_complete": False,
        },
        "production_eligible": False, "automatic_order": False,
        "block_reason": error or ("SOURCE_DATA_INCOMPLETE" if source_missing else
                                  "UNVERIFIED_EXECUTED_TRADE_COVERAGE"),
        "artifact_file": "output/sky_quickscan_information/latest_13col.json" if report else None,
    }


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    request_id = "INVALID"
    report = None
    error = None
    observation = None
    stage1 = None
    stage2 = None
    stage3 = None
    stage4 = None
    try:
        request_id = validate_request(json.loads(REQUEST.read_text(encoding="utf-8")))
        for argv in (
            [sys.executable, "-m", "research.sky_full_universe_information"],
            [sys.executable, "-m", "research.sky_13col_report",
             "--input", "output/sky_quickscan_information/full_universe.json",
             "--output", "output/sky_quickscan_information/latest_13col.md",
             "--json-output", "output/sky_quickscan_information/latest_13col.json"],
        ):
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=240, check=False)
            if proc.returncode != 0:
                raise RuntimeError(f"RUNNER_FAILED:{argv[2]}:EXIT_{proc.returncode}")
        report = json.loads(Path("output/sky_quickscan_information/latest_13col.json").read_text(encoding="utf-8"))
        validate_report(report)
        observation = json.loads(Path("output/sky_quickscan_information/full_universe.json").read_text(encoding="utf-8"))
        if observation.get("universe_count") != report.get("row_count"):
            raise ValueError("UNIVERSE_COUNT_MISMATCH")
        expected = {str(item.get("symbol")) for item in observation.get("all_symbols", [])
                    if isinstance(item, dict)}
        actual = {str(item["股票代碼"]) for item in report["rows"]}
        if expected != actual:
            raise ValueError("UNIVERSE_SYMBOL_SET_MISMATCH")
        stage1 = screen_stage1(observation)
        Path("output/sky_quickscan_information/stage1_candidates.json").write_text(
            json.dumps(stage1, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stage2 = verify_stage2(stage1)
        Path("output/sky_quickscan_information/stage2_quote_evidence.json").write_text(
            json.dumps(stage2, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stage3 = probe_v14_candles(stage2)
        Path("output/sky_quickscan_information/v14_ticker_5m_evidence.json").write_text(
            json.dumps(stage3, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stage4 = write_candidate_chain(stage1, stage2, stage3,
            "output/sky_quickscan_information/candidate_e2e_chain.json")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        error = str(exc)[:160]
        report = None
    status = make_status(request_id, report, error, observation, stage1, stage2, stage3, stage4)
    # #531: attest the *same* existing run/receipt without another market call.
    # Any missing, foreign, stale or blocked status must remain NO_TRADE.
    if status["status"] == "REPORT_READY_RESEARCH_ONLY":
        try:
            status["readback"] = validate_scan_readback(
                status,
                expected_run_id=str(os.getenv("GITHUB_RUN_ID") or ""),
                expected_request_id=request_id,
                expected_head_sha=str(os.getenv("GITHUB_SHA") or ""),
            )
        except ValueError as exc:
            status["status"] = "DATA_BLOCKED_READBACK_INVALID"
            status["block_reason"] = f"READBACK:{str(exc)[:100]}"
            status["readback"] = {
                "status": "HOLD", "trade_action": "禁止交易",
                "production_eligible": False, "automatic_order": False,
            }
    else:
        status["readback"] = {
            "status": "HOLD", "trade_action": "禁止交易",
            "production_eligible": False, "automatic_order": False,
        }
    (OUTPUT / "latest.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in status.items() if k != "preview"}, ensure_ascii=False))
    if status["status"] != "REPORT_READY_RESEARCH_ONLY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
