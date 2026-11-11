"""Fail-closed readback of an extracted #512 live 5m JSON artifact.

This never calls Fugle and never approves Production. Caller supplies the
exact GitHub workflow run ID and head SHA independently from GitHub.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")


def _time(value):
    if not isinstance(value, str):
        raise ValueError("MISSING_TIME")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.utcoffset() is None:
        raise ValueError("NAIVE_TIME")
    return dt.astimezone(TPE)


def validate(receipt, *, expected_sha, expected_run_id):
    if receipt.get("schema") != "SKY_V14_TICKER_5M_RESEARCH_PROVENANCE_V1":
        raise ValueError("INVALID_SCHEMA")
    if not expected_sha or receipt.get("head_sha") != expected_sha:
        raise ValueError("SHA_MISMATCH")
    if not expected_run_id or str(receipt.get("run_id")) != str(expected_run_id):
        raise ValueError("RUN_ID_MISMATCH")
    if receipt.get("production_eligible") is not False or receipt.get("automatic_order") is not False:
        raise ValueError("NO_TRADE_VIOLATION")
    if receipt.get("rate_limited") is not False:
        raise ValueError("RATE_LIMITED_OR_UNKNOWN")
    if not isinstance(receipt.get("attempted_api_requests"), int) or not 0 < receipt["attempted_api_requests"] <= 4:
        raise ValueError("UNBOUNDED_API_REQUESTS")
    observation = _time(receipt.get("time_tpe"))
    samples = receipt.get("samples")
    if not isinstance(samples, list) or len(samples) != 2:
        raise ValueError("TWO_MARKET_EVIDENCE_REQUIRED")
    if {s.get("exchange") for s in samples if isinstance(s, dict)} != {"TWSE", "TPEx"}:
        raise ValueError("MARKET_MISMATCH")
    for sample in samples:
        if sample.get("production_eligible") is not False:
            raise ValueError("SAMPLE_TRADE_VIOLATION")
        if sample.get("source_identity_matches") is not True:
            raise ValueError("SOURCE_MISMATCH")
        if sample.get("candles_timeframe") != "5":
            raise ValueError("TIMEFRAME_MISMATCH")
        if sample.get("bar_sequence_valid") is not True:
            raise ValueError("BAR_SEQUENCE_INVALID")
        if sample.get("bar_timestamp_semantics_certified") is not False:
            raise ValueError("UNSUPPORTED_CERTIFICATION_CLAIM")
        if _time(sample.get("observation_time_tpe")) != observation:
            raise ValueError("OBSERVATION_TIME_MISMATCH")
        if _time(sample.get("ticker_received_at_tpe")) < observation:
            raise ValueError("TICKER_TIME_BEFORE_OBSERVATION")
        if _time(sample.get("candles_received_at_tpe")) < observation:
            raise ValueError("CANDLE_TIME_BEFORE_OBSERVATION")
        raw = sample.get("raw_five_min_candles")
        if not isinstance(raw, dict) or raw.get("symbol") != sample.get("symbol") or raw.get("exchange") != sample.get("exchange"):
            raise ValueError("RAW_SOURCE_MISMATCH")
        if str(raw.get("timeframe")) != "5" or raw.get("date") != observation.date().isoformat():
            raise ValueError("RAW_DATE_OR_TIMEFRAME_MISMATCH")
        bars = raw.get("data")
        if not isinstance(bars, list) or not bars:
            raise ValueError("MISSING_RAW_BARS")
        if len(bars) >= 100:
            raise ValueError("RAW_BARS_POSSIBLY_TRUNCATED")
        accepted = 0
        unfinished = 0
        future = 0
        previous = None
        last_stamp = None
        for bar in bars:
            stamp = _time(bar.get("date"))
            if stamp.date() != observation.date() or stamp.minute % 5 or stamp.second or stamp.microsecond:
                raise ValueError("INVALID_RAW_TIME_GRID")
            if previous is not None and stamp - previous != timedelta(minutes=5):
                raise ValueError("RAW_BAR_ORDER_OR_GAP")
            previous = stamp
            if stamp > observation:
                future += 1
            elif stamp + timedelta(minutes=5) > observation:
                unfinished += 1
            else:
                accepted += 1
                last_stamp = stamp
        for key, computed in (
            ("valid_today_five_min_bars", accepted),
            ("excluded_unfinished_five_min_bars", unfinished),
            ("rejected_future_five_min_bars", future),
        ):
            if sample.get(key) != computed:
                raise ValueError("BAR_COUNT_MISMATCH:" + key)
        expected_last = last_stamp.isoformat() if last_stamp else None
        if sample.get("last_feature_bar_time_tpe") != expected_last:
            raise ValueError("LAST_BAR_TIME_MISMATCH")
    # Data-readback only. Provider minute-bar semantics require independent
    # verification, so successful receipt validation is never final approval.
    return {"status": "ARTIFACT_DATA_READBACK_PASS_PENDING_PROVIDER_SEMANTICS",
            "head_sha": expected_sha, "run_id": str(expected_run_id),
            "markets": ["TWSE", "TPEx"], "production_eligible": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", type=Path)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    receipt = json.loads(args.json_path.read_text(encoding="utf-8"))
    print(json.dumps(validate(receipt, expected_sha=args.sha,
                              expected_run_id=args.run_id), ensure_ascii=False))


if __name__ == "__main__":
    main()
