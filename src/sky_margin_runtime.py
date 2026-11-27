"""SKY維持率: offline consumer for already collected research-only source bundles.

No provider HTTP, GitHub dispatch, broker access, account assumptions or orders.
Input fields are caller-supplied; successful parsing is NOT source certification.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from src.sky_margin_source_join import join_margin_sources

TPE = ZoneInfo("Asia/Taipei")
REQUIRED = (
    "official_universe", "universe_total", "official_universe_source",
    "ratio_by_symbol", "capital_by_symbol", "volume_by_symbol",
    "fugle_quotes_by_symbol", "observed_at", "previous_session_date",
)


def evaluate_margin_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Run existing #752 join without treating caller declarations as proof."""
    if not isinstance(bundle, Mapping):
        raise ValueError("INVALID_MARGIN_BUNDLE")
    missing = [name for name in REQUIRED if name not in bundle]
    if missing:
        raise ValueError("MISSING_MARGIN_INPUT:" + ",".join(missing))
    if set(bundle) - set(REQUIRED):
        raise ValueError("UNRECOGNIZED_MARGIN_INPUT")
    timestamp = bundle["observed_at"]
    if not isinstance(timestamp, str):
        raise ValueError("INVALID_OBSERVATION_TIME")
    try:
        observed_at = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise ValueError("INVALID_OBSERVATION_TIME") from exc
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("OBSERVATION_TIMEZONE_REQUIRED")
    # Normalize explicitly to TPE, preventing UTC midnight/session rollover.
    observed_at = observed_at.astimezone(TPE)
    result = join_margin_sources(
        official_universe=bundle["official_universe"],
        universe_total=bundle["universe_total"],
        official_universe_source=bundle["official_universe_source"],
        ratio_by_symbol=bundle["ratio_by_symbol"],
        capital_by_symbol=bundle["capital_by_symbol"],
        volume_by_symbol=bundle["volume_by_symbol"],
        fugle_quotes_by_symbol=bundle["fugle_quotes_by_symbol"],
        observed_at=observed_at,
        previous_session_date=bundle["previous_session_date"],
    )
    # Caller supplied origin strings are not independent TWSE/TPEx/Fugle proofs.
    result["execution_mode"] = "OFFLINE_CALLER_SUPPLIED_RESEARCH"
    result["execution_status"] = "HOLD_LIVE_SOURCE_AND_MOBILE_E2E"
    result["source_certified"] = False
    result["github_run_verified"] = False
    result["artifact_independent_readback_verified"] = False
    result["mobile_e2e_verified"] = False
    result["new_entry_authorized"] = False
    result["buy_eligible"] = False
    result["trade_status"] = "NO_TRADE"
    result["observed_at_tpe"] = observed_at.isoformat()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline SKY維持率 research bundle consumer")
    parser.add_argument("--input-json", required=True, type=Path)
    args = parser.parse_args(argv)
    # Explicit input only: never fetch missing rows or auto-run paid providers.
    try:
        raw = json.loads(args.input_json.read_text(encoding="utf-8"))
        result = evaluate_margin_bundle(raw)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({
            "execution_status": "HOLD_INVALID_OR_MISSING_INPUT",
            "reason": str(exc), "trade_status": "NO_TRADE",
            "new_entry_authorized": False, "production_eligible": False,
        }, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
