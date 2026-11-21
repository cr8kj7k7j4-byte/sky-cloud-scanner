"""Independent, read-only provenance and causal validation for existing Fugle 5m receipts.

Adapted from legacy #512 source checks; intentionally no simulated ledger,
paper orders, fills, replay, signals, or provider/API calls. Caller must obtain
GitHub run/artifact metadata independently; this module cannot authenticate it.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
import re

SCHEMA = "SKY_INDEPENDENT_5M_SOURCE_PROOF_V1"
SOURCE_SCHEMA = "SKY_V14_TICKER_5M_RESEARCH_PROVENANCE_V1"
TPE = timezone(timedelta(hours=8))
SHA = re.compile(r"^[0-9a-f]{40}$")


def aware(value):
    if not isinstance(value, str):
        raise ValueError("TIMESTAMP_REQUIRED")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_TIMESTAMP") from exc
    if result.utcoffset() is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return result.astimezone(timezone.utc)


def validate(payload, *, run, artifact):
    """Validate externally supplied GitHub API metadata and the receipt.

    run/artifact must be fetched by a trusted caller, NOT copied from payload.
    This checks consistency, not whether the caller truly contacted GitHub.
    """
    if not isinstance(run, dict) or not isinstance(artifact, dict):
        raise ValueError("INDEPENDENT_GITHUB_METADATA_REQUIRED")
    run_id = run.get("id")
    sha = run.get("head_sha")
    artifact_id = artifact.get("id")
    if (type(run_id) is not int or run_id <= 0
            or not isinstance(sha, str) or not SHA.fullmatch(sha)
            or run.get("status") != "completed" or run.get("conclusion") != "success"
            or run.get("repository", {}).get("full_name") != "cr8kj7k7j4-byte/sky-cloud-scanner"
            or type(artifact_id) is not int or artifact_id <= 0
            or artifact.get("expired") is not False
            or str(artifact.get("workflow_run", {}).get("id")) != str(run_id)):
        raise ValueError("UNTRUSTED_GITHUB_SOURCE")
    if (not isinstance(payload, dict) or payload.get("schema") != SOURCE_SCHEMA
            or str(payload.get("run_id")) != str(run_id)
            or payload.get("head_sha") != sha
            or payload.get("production_eligible") is not False
            or payload.get("automatic_order") is not False
            or not isinstance(payload.get("samples"), list)):
        raise ValueError("SOURCE_RECEIPT_MISMATCH")
    observed = aware(payload.get("time_tpe"))
    if observed.astimezone(TPE).date() != aware(artifact.get("created_at")).astimezone(TPE).date():
        raise ValueError("SOURCE_UPLOAD_DATE_MISMATCH")
    output = []
    seen = set()
    for sample in payload["samples"]:
        if not isinstance(sample, dict):
            raise ValueError("INVALID_SAMPLE")
        key = (sample.get("exchange"), sample.get("symbol"))
        if (key[0] not in ("TWSE", "TPEx") or not isinstance(key[1], str)
                or not key[1].isascii() or not key[1].isdigit() or key in seen):
            raise ValueError("DUPLICATE_OR_INVALID_SOURCE")
        seen.add(key)
        raw = sample.get("raw_five_min_candles")
        if (not isinstance(raw, dict) or raw.get("symbol") != key[1]
                or raw.get("exchange") != key[0] or str(raw.get("timeframe")) != "5"
                or not isinstance(raw.get("data"), list)):
            raise ValueError("INVALID_PROVIDER_CANDLE_SOURCE")
        accepted = 0
        future = 0
        unfinished = 0
        previous = None
        last = None
        for bar in raw["data"]:
            if not isinstance(bar, dict):
                raise ValueError("INVALID_BAR")
            stamp = aware(bar.get("date"))
            local = stamp.astimezone(TPE)
            if (local.date() != observed.astimezone(TPE).date()
                    or local.minute % 5 or local.second or local.microsecond
                    or (previous is not None and stamp - previous != timedelta(minutes=5))):
                raise ValueError("NONCAUSAL_OR_NONCONTIGUOUS_BAR")
            previous = stamp
            for k in ("open", "high", "low", "close"):
                v = bar.get(k)
                if type(v) not in (int, float) or not math.isfinite(v) or v <= 0:
                    raise ValueError("INVALID_OHLC")
            if (bar["low"] > min(bar["open"], bar["close"])
                    or bar["high"] < max(bar["open"], bar["close"])
                    or bar["low"] > bar["high"]):
                raise ValueError("INVALID_OHLC_ENVELOPE")
            volume = bar.get("volume")
            if type(volume) not in (int, float) or not math.isfinite(volume) or volume < 0:
                raise ValueError("INVALID_VOLUME")
            if stamp > observed:
                future += 1
            elif stamp + timedelta(minutes=5) > observed:
                unfinished += 1
            else:
                accepted += 1
                last = stamp
        if (accepted != sample.get("valid_today_five_min_bars")
                or future != sample.get("rejected_future_five_min_bars", 0)
                or unfinished != sample.get("excluded_unfinished_five_min_bars", 0)
                or sample.get("bar_sequence_valid") is not True
                or (last.isoformat() if last else None) !=
                   (aware(sample["last_feature_bar_time_tpe"]).isoformat()
                    if sample.get("last_feature_bar_time_tpe") else None)):
            raise ValueError("SOURCE_COUNTS_OR_LAST_BAR_MISMATCH")
        output.append({"exchange": key[0], "symbol": key[1],
                       "completed_bars": accepted, "excluded_unfinished": unfinished,
                       "rejected_future": future})
    return {"schema": SCHEMA, "source_run_id": run_id, "source_sha": sha,
            "source_artifact_id": artifact_id, "samples": output,
            "source_metadata_consistent": True,
            "github_metadata_independently_fetched_by_this_module": False,
            "bar_timestamp_semantics_certified": False,
            "vwap_certified": False, "production_eligible": False,
            "automatic_order": False, "trade_action": "禁止交易"}
