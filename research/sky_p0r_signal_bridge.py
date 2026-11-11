"""Fail-closed join from pre-existing signal receipts to independently captured bars.

No market requests, no broker connection, no inferred signals or fills.
A signal originating AFTER a candle snapshot cannot be backdated into it.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from research.sky_p0r_market_event_producer import produce


def _at(value):
    if not isinstance(value, str):
        raise ValueError("TIMESTAMP_REQUIRED")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("TIMESTAMP_INVALID") from exc
    if stamp.utcoffset() is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return stamp.astimezone(timezone.utc)


def _hold(reason, *, source_run_id=None, signal_run_id=None):
    return {"schema": "SKY_P0R_SIGNAL_TO_PAPER_CHAIN_V1",
            "verdict": "INSUFFICIENT_DATA", "reason": reason,
            "bar_source_run_id": source_run_id,
            "signal_source_run_id": signal_run_id,
            "paper_events_produced": 0, "paper_fill_count": 0,
            "reconciled": False, "production_eligible": False,
            "automatic_order": False, "trade_action": "禁止交易"}


def join(verified_bars, signal_receipt=None, *, external_signal_provenance_verified=False):
    """Convert only an explicitly precommitted signal into input for existing simulator.

    Caller is responsible for independently downloading and verifying the signal
    artifact; this function never upgrades caller-supplied provenance to verified.
    """
    if not isinstance(verified_bars, dict) or verified_bars.get("schema") != "SKY_P0R_VERIFIED_SOURCE_BARS_V1":
        raise ValueError("VERIFIED_BARS_REQUIRED")
    if (verified_bars.get("production_eligible") is not False
            or verified_bars.get("automatic_order") is not False
            or verified_bars.get("market_bars_available") is not True):
        raise ValueError("UNTRUSTED_MARKET_BARS")
    source_run = verified_bars.get("source_run_id")
    observation = _at(verified_bars.get("observed_at"))
    if signal_receipt is None:
        return _hold("PRECOMMITTED_SIGNAL_ARTIFACT_MISSING", source_run_id=source_run), None
    if not isinstance(signal_receipt, dict):
        raise ValueError("INVALID_SIGNAL_RECEIPT")
    if (signal_receipt.get("schema") != "SKY_PRECOMMITTED_PAPER_SIGNAL_V1"
            or signal_receipt.get("production_eligible") is not False
            or signal_receipt.get("automatic_order") is not False):
        raise ValueError("UNTRUSTED_SIGNAL_SCHEMA")
    for key in ("signal_run_id", "signal_sha", "signal_artifact_id", "signal_scan_id"):
        if not isinstance(signal_receipt.get(key), str) or not signal_receipt[key]:
            raise ValueError("SIGNAL_PROVENANCE_REQUIRED")
    # A supplied flag is not external proof: this explicit pair of fields must
    # originate from an independently downloaded and inspected signal receipt.
    # Do not treat this join as proof of independent verification.
    published = _at(signal_receipt.get("published_at"))
    signal = signal_receipt.get("signal")
    if not isinstance(signal, dict) or signal.get("market_scan_id") != signal_receipt["signal_scan_id"]:
        raise ValueError("SIGNAL_SCAN_ID_MISMATCH")
    signal_at = _at(signal.get("signal_time"))
    if signal_at > published:
        raise ValueError("SIGNAL_PUBLISHED_BEFORE_CREATION")
    if published > observation:
        return _hold("SIGNAL_PUBLISHED_AFTER_BAR_OBSERVATION",
                     source_run_id=source_run, signal_run_id=signal_receipt["signal_run_id"]), None
    if signal_receipt["signal_run_id"] == source_run:
        raise ValueError("SIGNAL_AND_BAR_RUN_NOT_INDEPENDENT")
    if external_signal_provenance_verified is not True:
        return _hold("SIGNAL_ARTIFACT_NOT_INDEPENDENTLY_VERIFIED",
                     source_run_id=source_run, signal_run_id=signal_receipt["signal_run_id"]), None
    symbol = signal.get("symbol")
    sources = verified_bars.get("bar_sources")
    if not isinstance(sources, dict) or symbol not in sources:
        return _hold("SIGNAL_SYMBOL_NOT_IN_VERIFIED_BARS",
                     source_run_id=source_run, signal_run_id=signal_receipt["signal_run_id"]), None
    bars = sources[symbol].get("completed_bars")
    if not isinstance(bars, list) or not bars:
        raise ValueError("COMPLETED_BARS_REQUIRED")
    if any(_at(b["completed_at"]) > observation for b in bars):
        raise ValueError("FUTURE_OR_INCOMPLETE_BARS")
    if any(b.get("source_type") != "MARKET_OBSERVATION" for b in bars):
        raise ValueError("BAR_SOURCE_MISMATCH")
    if not any(_at(b["started_at"]) > published for b in bars):
        return _hold("NO_CANDLE_START_AFTER_SIGNAL_PUBLICATION",
                     source_run_id=source_run, signal_run_id=signal_receipt["signal_run_id"]), None
    context = {"run_id": str(source_run), "scan_id": signal_receipt["signal_scan_id"],
               "source_artifact": bars[0]["source_artifact"],
               "simulator_version": "SKY_P0R_NEXT_BAR_OPEN_ESTIMATE_RESEARCH_V1",
               "observed_at": verified_bars["observed_at"]}
    payload = {"context": context, "signal": signal, "completed_bars": bars}
    # Producer checks canonical P0-R / P0-X risk, full explicit cost inputs,
    # completed exits and event→journal reconciliation; cannot infer a fill.
    # Publication may postdate signal_time, so do not give the simulator the
    # earlier time to trade from; require strict equality as a safe precommit.
    if published != signal_at:
        return _hold("SIGNAL_COMMIT_TIME_NOT_EQUAL_TO_SIGNAL_TIME",
                     source_run_id=source_run, signal_run_id=signal_receipt["signal_run_id"]), None
    result = produce(payload)
    out = {"schema": "SKY_P0R_SIGNAL_TO_PAPER_CHAIN_V1",
           "verdict": result["verdict"], "reason": None,
           "bar_source_run_id": source_run,
           "signal_source_run_id": signal_receipt["signal_run_id"],
           "signal_source_sha": signal_receipt["signal_sha"],
           "signal_artifact_id": signal_receipt["signal_artifact_id"],
           "paper_events_produced": len(result.get("events", [])),
           "paper_fill_count": len(result.get("closed_fills", [])),
           "reconciled": bool(result.get("ledger_audit", {}).get("reconciled")),
           "signal_artifact_independently_verified": False,
           "simulated_fill_origin_independently_verified": False,
           "production_eligible": False, "automatic_order": False,
           "trade_action": "禁止交易"}
    return out, payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars", required=True)
    parser.add_argument("--signal", required=True)
    parser.add_argument("--status", required=True)
    args = parser.parse_args()
    bars = json.loads(Path(args.bars).read_text(encoding="utf-8"))
    manifest = Path(args.signal)
    signal = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else None
    result, _ = join(bars, signal)
    path = Path(args.status)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
