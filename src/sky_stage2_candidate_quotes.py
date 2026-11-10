"""Bounded, read-only Stage-2 Fugle individual quote evidence for Stage-1 candidates.

No orders, no promotion, no whole-market qualification from a small sample.
"""
from __future__ import annotations

import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from src.fugle import get_quote
from src.realtime_quote_evidence import fugle_executed_trade

TPE = ZoneInfo("Asia/Taipei")
MAX_QUERIES = 6
SLEEP_SECONDS = 1.0


def select(stage1, *, per_market=3):
    """Deterministic balanced sampling; strict upper limit even if inputs are large."""
    if stage1.get("schema") != "SKY_STAGE1_FUGLE_SNAPSHOT_CANDIDATES_V1":
        raise ValueError("INVALID_STAGE1_SOURCE")
    if not isinstance(per_market, int) or not 1 <= per_market <= 3:
        raise ValueError("INVALID_SAMPLE_SIZE")
    output = []
    for exchange in ("TWSE", "TPEx"):
        items = [r for r in stage1.get("candidates", [])
                 if r.get("exchange") == exchange and r.get("production_eligible") is False]
        output.extend(items[:per_market])
    return output


def verify(stage1, *, quote_fn=get_quote, sleep_fn=time.sleep, now_fn=None):
    now_fn = now_fn or (lambda: datetime.now(TPE))
    picked = select(stage1)
    results = []
    total_requests = 0
    rate_limited = 0
    for candidate in picked:
        symbol = str(candidate["symbol"])
        row = {"symbol": symbol, "exchange": candidate["exchange"],
               "stage1_observed_price": candidate.get("observed_price"),
               "classification": "未分級", "action": "等待",
               "production_eligible": False, "executed_trade_verified": False}
        try:
            total_requests += 1
            payload = quote_fn(symbol)
            quote = payload.get("data", payload) if isinstance(payload, dict) else payload
            price, executed_at, reason = fugle_executed_trade(quote, now=now_fn(),
                                                               max_age_seconds=180)
            row.update({"status": reason, "verified_trade_price": price,
                        "last_trade_time": executed_at.isoformat() if executed_at else None,
                        "executed_trade_verified": reason == "FRESH_EXECUTED_TRADE"})
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 429:
                rate_limited += 1
            row.update({"status": "RATE_LIMITED" if status == 429 else
                                 "PLAN_RESTRICTED" if status in (401, 403) else "HTTP_ERROR",
                        "http_status": status})
        except PermissionError:
            row["status"] = "PLAN_RESTRICTED"
        except (requests.RequestException, ValueError, TypeError) as exc:
            row.update({"status": "SOURCE_ERROR", "error_type": type(exc).__name__})
        results.append(row)
        sleep_fn(SLEEP_SECONDS)
        if rate_limited:
            # Fail closed immediately; never hammer a provider returning 429.
            break
    return {
        "schema": "SKY_STAGE2_BOUNDED_QUOTE_EVIDENCE_V1",
        "checked_at_tpe": now_fn().isoformat(),
        "stage1_candidate_count": stage1.get("candidate_count"),
        "selected_count": len(picked), "attempted_count": total_requests,
        "verified_executed_count": sum(r["executed_trade_verified"] for r in results),
        "rate_limited_count": rate_limited,
        "request_pacing_seconds": SLEEP_SECONDS,
        "max_requests_per_run": MAX_QUERIES,
        "scope": "CANDIDATE_SAMPLE_ONLY",
        "rate_limit_plan_verified": False,
        "results": results,
        "production_eligible": False,
        "automatic_order": False,
        "trade_decision": "🔴 禁止新進場、未驗證通過",
    }
