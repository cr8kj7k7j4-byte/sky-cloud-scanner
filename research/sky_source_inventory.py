"""Shared source-inventory writer for existing intraday and postmarket jobs.

Pure local file hashing. No network, Fugle, exchange calendar or trade claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "SKY_W0_SAME_RUN_SOURCE_INVENTORY_V1"
ROOT = Path("output/sky_quickscan_information")
SOURCES = {
    "operational_snapshot_gate": Path("output/latest.json"),
    "full_market_reference": ROOT / "full_universe.json",
    "individual_executed_trade_samples": ROOT / "fugle_execution_samples.json",
    "five_minute_candle_probe": ROOT / "v14_ticker_5m_evidence.json",
    "independent_tick_trades_vwap_receipt": ROOT / "independent_trades_vwap_evidence.json",
}


def build_inventory(*, base: Path, run_id: str, attempt: str, sha: str,
                    event: str, mode: str) -> dict:
    """Hash local source bytes, never declare provider semantics verified."""
    if mode not in ("intraday", "postmarket_observation"):
        raise ValueError("UNSUPPORTED_SOURCE_INVENTORY_MODE")
    if (not run_id.isdigit() or not attempt.isdigit() or len(sha) != 40
            or any(c not in "0123456789abcdef" for c in sha)):
        raise ValueError("INVALID_GITHUB_RUN_PROVENANCE")
    sources = {}
    for key, path in SOURCES.items():
        f = base / path
        item = {
            "path": path.as_posix(),
            "status": "HOLD_SOURCE_NOT_CAPTURED",
            "raw_provider_source_certified": False,
        }
        if f.is_file() and not f.is_symlink() and f.resolve().is_relative_to(base.resolve()):
            data = f.read_bytes()
            item.update({
                "byte_count": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
            try:
                parsed = json.loads(data)
                if not isinstance(parsed, (dict, list)):
                    raise ValueError("JSON_ROOT_NOT_OBJECT_OR_ARRAY")
                item["status"] = "FILE_PRESENT_NOT_SOURCE_CERTIFIED"
                if isinstance(parsed, dict):
                    for field in ("data_time", "observed_at", "quote_observed_at",
                                  "captured_at", "candles_received_at_tpe"):
                        if isinstance(parsed.get(field), str):
                            item[field] = parsed[field]
            except (ValueError, UnicodeDecodeError):
                item["status"] = "HOLD_INVALID_JSON"
        sources[key] = item
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "run_attempt": attempt,
        "head_sha": sha,
        "event_name": event,
        "capture_mode": mode,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_inventory": sources,
        "live_five_minute_requests": "DISABLED_V5_4",
        "independent_tick_vwap_requests": "DISABLED_V5_4",
        "five_minute_pit_certified": False,
        "volume_units_certified": False,
        "independent_tick_vwap_certified": False,
        "production_eligible": False,
        "trade_action": "禁止交易",
        "note": ("Presence and hashes do not prove source semantics, freshness, "
                 "5m PIT, units or VWAP. Missing evidence remains HOLD."),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("intraday", "postmarket_observation"), required=True)
    args = parser.parse_args()
    base = Path(".")
    receipt = build_inventory(
        base=base,
        run_id=os.environ["GITHUB_RUN_ID"],
        attempt=os.environ["GITHUB_RUN_ATTEMPT"],
        sha=os.environ["GITHUB_SHA"],
        event=os.environ["GITHUB_EVENT_NAME"],
        mode=args.mode,
    )
    target = ROOT / "same_run_source_inventory.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("W0_SOURCE_INVENTORY_WRITTEN:", target)
    for name, item in receipt["source_inventory"].items():
        print(name, item["status"])


if __name__ == "__main__":
    main()
