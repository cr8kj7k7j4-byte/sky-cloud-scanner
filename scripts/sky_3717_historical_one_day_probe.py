"""W0 #363: EXACT one-day owner-approved Fugle history research diagnostic.

No other market endpoints or automatic retries. Repeated owner-authorized
observations are allowed; request count is recorded, never a data-quality gate.
No order, strategy promotion or secrets in output. HTTP status is retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src import fugle
from src.sky_historical_5m_research import evaluate, HOLD

TPE = timezone(timedelta(hours=8))
TARGET_SYMBOL = "3717"
TARGET_DATE = "2026-11-27"

class RecordingSession:
    """requests-compatible evidence recorder with no fixed request-count gate.

    Every GET still passes Fugle entitlement, request-identity and rate pacing.
    This recorder never retries automatically and never stores secret headers.
    """
    def __init__(self, base=None):
        if base is None:
            import requests
            base = requests
        self.base = base
        self.status_code = None
        self.request_count = 0

    def get(self, url, *, params, headers, timeout):
        if not url.endswith("/historical/candles/3717"):
            raise RuntimeError("HISTORICAL_ENDPOINT_DENIED")
        if params.get("from") != TARGET_DATE or params.get("to") != TARGET_DATE:
            raise RuntimeError("HISTORICAL_DATE_DENIED")
        self.request_count += 1
        response = self.base.get(url, params=params, headers=headers, timeout=timeout)
        self.status_code = int(response.status_code)
        return response


def run(*, symbol=TARGET_SYMBOL, source_date=TARGET_DATE, session=None,
        observed_at=None):
    now = observed_at or datetime.now(TPE)
    result = {
        "schema": "SKY_3717_HISTORICAL_ONE_DAY_PROBE_V1",
        "symbol": symbol, "source_date": source_date,
        "source": "Fugle MarketData Historical Candles",
        "endpoint": "/historical/candles/3717", "timeframe": "5",
        "observed_at_tpe": now.astimezone(TPE).isoformat(),
        "http_status": None, "request_count": 0,
        "http_request_count_is_evidence_gate": False,
        "status": HOLD, "reason": "NOT_EXECUTED",
        "five_minute_status": "HOLD",
        "execution_authorized": False, "production_eligible": False,
        "automatic_order": False, "independent_vwap_certified": False,
    }
    if symbol != TARGET_SYMBOL or source_date != TARGET_DATE:
        result["reason"] = "DIAGNOSTIC_SCOPE_DENIED"
        return result
    if date.fromisoformat(source_date) >= now.astimezone(TPE).date():
        result["reason"] = "UNFINISHED_SESSION_DENIED"
        return result
    s = session or RecordingSession()
    try:
        payload = fugle.get_historical_candles_5m(symbol, source_date, session=s)
        result["http_status"] = s.status_code
        result["request_count"] = s.request_count
        if not isinstance(payload, dict):
            result["reason"] = "NON_OBJECT_PROVIDER_RESPONSE"
            return result
        # Provider may omit metadata in a historical response. Never fabricate
        # an exchange identity from a stock code. Keep verified request and
        # response identities separate.
        response_meta = {k: payload.get(k) for k in ("symbol", "exchange", "timeframe")}
        result["provider_metadata_present"] = {k: k in payload for k in response_meta}
        result["provider_metadata"] = response_meta
        raw = payload.get("data")
        result["row_count"] = len(raw) if isinstance(raw, list) else None
        if isinstance(raw, list):
            raw_bytes = json.dumps(raw, sort_keys=True, ensure_ascii=True,
                                   separators=(",", ":"), allow_nan=False).encode()
            result["provider_bars_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
            result["first_bar_start_tpe"] = raw[0].get("date") if raw and isinstance(raw[0], dict) else None
            result["last_bar_start_tpe"] = raw[-1].get("date") if raw and isinstance(raw[-1], dict) else None
        # Validator requires true provider response metadata, so missing
        # provenance remains HOLD instead of inventing exchange/timeframe.
        validation = evaluate(symbol, source_date, payload, observed_at=now)
        result["historical_5m_research"] = validation
        result["status"] = validation["status"]
        result["reason"] = validation["reason"]
        result["five_minute_status"] = "HOLD_LIVE_TRADES_NOT_CERTIFIED"
    except Exception as exc:
        result["http_status"] = s.status_code
        result["request_count"] = s.request_count
        result["reason"] = ("PROVIDER_HTTP_" + str(s.status_code)
                            if s.status_code is not None
                            else "HISTORICAL_TRANSPORT_ERROR")
        result["error_type"] = type(exc).__name__
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--out-dir", default="output/single_stock")
    args = parser.parse_args()
    result = run(symbol=args.symbol, source_date=args.date)
    root = Path(args.out_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / (args.symbol + "-5m-source.json")).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    lines = [
        "🟡 Sky 3717｜Fugle 指定日歷史 5m 來源驗證",
        f"資料交易日：{result['source_date']}（Asia/Taipei）",
        f"查詢 HTTP：{result['http_status'] if result['http_status'] is not None else '待確認'}",
        f"累計觀察請求數：{result['request_count']}（非研究資料通過門檻）",
        f"歷史資料狀態：{result['status']}",
        f"資料拒絕／觀察原因：{result['reason']}",
        f"歷史棒數：{result.get('row_count') if result.get('row_count') is not None else '待確認'}",
        f"歷史棒 SHA256：{result.get('provider_bars_sha256', '待確認')}",
        "此文件只認證指定日歷史研究來源，不是逐筆成交、正式 VWAP 或交易訊號。",
        "新進場：禁止交易；自動下單：停用。",
    ]
    (root / (args.symbol + "-5m-source.md")).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: result.get(k) for k in
                     ("symbol", "source_date", "http_status", "request_count",
                      "row_count", "status", "reason")}, ensure_ascii=False))
    # Each explicit run records one source observation by current call design.
    # Reusing a recorder across runs is permitted; there is NO maximum count.
    # Every actual request still passes Fugle provider rate/entitlement guards.
    # The independent reader checks bytes, not permission or market freshness.


if __name__ == "__main__":
    main()
