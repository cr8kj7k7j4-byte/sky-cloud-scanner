"""SKY維持率 legacy shortcut: price-only research observations (no ratio screen).

The user retired the margin-ratio/estimated-source requirement, paid-in capital,
and previous-day volume from THIS command's observation mode. This is NOT a
margin-maintenance selection strategy. Historical four-factor modules remain
archived for reproducibility, not called here.
No network, credentials, API requests, broker data, order or Production action.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from src.sky_margin_a2_quote_bridge import margin_row_with_a2_quote

TPE = ZoneInfo("Asia/Taipei")
REQUIRED = (
    "official_universe", "universe_total", "official_universe_source",
    "fugle_quotes_by_symbol", "observed_at",
)


def evaluate_margin_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Observe prices < 100; never claim margin ratio or trading eligibility."""
    if not isinstance(bundle, Mapping):
        raise ValueError("INVALID_PRICE_OBSERVATION_BUNDLE")
    missing = [key for key in REQUIRED if key not in bundle]
    if missing:
        raise ValueError("MISSING_PRICE_OBSERVATION_INPUT:" + ",".join(missing))
    if set(bundle) - set(REQUIRED):
        raise ValueError("RETIRED_OR_UNRECOGNIZED_SCREEN_INPUT")
    timestamp = bundle["observed_at"]
    if not isinstance(timestamp, str):
        raise ValueError("INVALID_OBSERVATION_TIME")
    try:
        observed = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise ValueError("INVALID_OBSERVATION_TIME") from exc
    if observed.utcoffset() is None:
        raise ValueError("OBSERVATION_TIMEZONE_REQUIRED")
    observed = observed.astimezone(TPE)
    universe = bundle["official_universe"]
    total = bundle["universe_total"]
    source = bundle["official_universe_source"]
    quotes = bundle["fugle_quotes_by_symbol"]
    if not isinstance(universe, (list, tuple)):
        raise ValueError("INVALID_OFFICIAL_UNIVERSE")
    if isinstance(total, bool) or not isinstance(total, int) or total < 1 or len(universe) > total:
        raise ValueError("INVALID_OFFICIAL_UNIVERSE_TOTAL")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("MISSING_UNIVERSE_SOURCE")
    if not isinstance(quotes, Mapping):
        raise ValueError("INVALID_A2_FEED")
    symbols, selected, rejected = set(), [], []
    for item in universe:
        if not isinstance(item, Mapping):
            raise ValueError("INVALID_UNIVERSE_RECORD")
        symbol = str(item.get("symbol") or "").strip()
        market = item.get("exchange")
        if not symbol.isdigit() or not 4 <= len(symbol) <= 6 or market not in ("TWSE", "TPEx"):
            raise ValueError("INVALID_UNIVERSE_IDENTITY")
        if symbol in symbols:
            raise ValueError("DUPLICATE_OFFICIAL_SYMBOL")
        symbols.add(symbol)
        quote = quotes.get(symbol)
        row = margin_row_with_a2_quote({"symbol": symbol, "exchange": market}, quote, observed_at=observed)
        if row.get("price_evidence") != "EXECUTED_TRADE":
            rejected.append({"symbol": symbol, "reason": row.get("price_reject_reason") or "MISSING_A2"})
            continue
        price = Decimal(row["last_trade_price_twd"])
        if price >= 100:
            rejected.append({"symbol": symbol, "reason": "PRICE_NOT_BELOW_100"})
            continue
        selected.append({
            "symbol": symbol, "exchange": market,
            "observed_price_twd": str(price),
            "price_trade_time_tpe": row["price_trade_time_tpe"],
            "price_source": row["price_source"],
            "price_origin_verified": False,
            "screening_mode": "PRICE_ONLY_OBSERVATION",
            "margin_ratio_screened": False,
            "capital_screened": False,
            "previous_volume_screened": False,
            "action": "觀察", "buy_eligible": False,
        })
    if set(quotes) - symbols:
        raise ValueError("EXTRA_A2_SYMBOLS")
    selected.sort(key=lambda item: (Decimal(item["observed_price_twd"]), item["symbol"]))
    complete = len(universe) == total
    return {
        "schema": "SKY_PRICE_ONLY_OBSERVATION_V1",
        "legacy_command": "SKY維持率",
        "mode": "PRICE_ONLY_OBSERVATION",
        "status": "HOLD_SOURCE_UNVERIFIED" if complete else "HOLD_INCOMPLETE_UNIVERSE",
        "execution_status": "HOLD_REAL_SOURCE_AND_MOBILE_E2E",
        "observation_date": observed.date().isoformat(),
        "observed_at_tpe": observed.isoformat(),
        "universe_total": total, "rows_received": len(universe),
        "universe_source": source,
        "official_universe_independently_verified": False,
        "a2_raw_http_origin_verified": False,
        "provider_entitlement_verified": False,
        "coverage_complete": complete,
        "screened_count": len(selected),
        "rejected_count": len(rejected),
        "candidates": selected[:10] if complete else [],
        "rejections": rejected,
        "retired_requirements": [
            "margin_ratio_estimate_and_source",
            "paid_in_capital",
            "previous_session_volume",
        ],
        "liquidity_unverified": True,
        "strategy_verified": False,
        "cost_after_rr_verified": False,
        "risk_p0r_verified": False,
        "github_run_verified": False,
        "artifact_independent_readback_verified": False,
        "mobile_e2e_verified": False,
        "production_eligible": False,
        "new_entry_authorized": False,
        "buy_eligible": False,
        "trade_status": "NO_TRADE",
        "reason": "Price-only observation is not a margin-maintenance strategy; source, liquidity, strategy, cost and P0-R not certified.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline price-only research observation")
    parser.add_argument("--input-json", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.input_json.read_text(encoding="utf-8"))
        result = evaluate_margin_bundle(data)
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
