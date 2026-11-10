"""Sky stage-1 paid Fugle full-market snapshot candidate screening.

Observation-only discovery. It cannot certify last trade, liquidity, spreads,
model score, A+ eligibility or issue a buy instruction.
"""
from __future__ import annotations

from datetime import datetime
import math

SCHEMA = "SKY_STAGE1_FUGLE_SNAPSHOT_CANDIDATES_V1"
MAX_PRICE_TWD = 100.0


def positive(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def screen(report: dict, *, max_price: float = MAX_PRICE_TWD) -> dict:
    """Preserve full audit counts and avoid treating snapshot time as last trade."""
    if report.get("schema") != "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1":
        raise ValueError("INVALID_SOURCE_SCHEMA")
    checked_at = datetime.fromisoformat(report["checked_at_tpe"])
    if checked_at.utcoffset() is None:
        raise ValueError("NAIVE_CHECKED_AT")
    if not 0 < max_price <= MAX_PRICE_TWD:
        raise ValueError("INVALID_PRICE_LIMIT")
    rows = report.get("all_symbols")
    if not isinstance(rows, list) or len(rows) != report.get("universe_count"):
        raise ValueError("UNIVERSE_INCOMPLETE")
    reasons: dict[str, int] = {}
    seen = set()
    selected = []
    markets = {"TWSE": {"universe": 0, "candidates": 0},
               "TPEx": {"universe": 0, "candidates": 0}}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("INVALID_UNIVERSE_ROW")
        symbol = str(row.get("symbol") or "")
        exchange = row.get("exchange")
        key = (exchange, symbol)
        if key in seen:
            raise ValueError("DUPLICATE_SYMBOL")
        seen.add(key)
        if exchange not in markets:
            raise ValueError("INVALID_EXCHANGE")
        markets[exchange]["universe"] += 1
        price = positive(row.get("last_price"))
        volume = positive(row.get("volume"))
        # An observed snapshot must be from today's trading session.
        # A prior-day or trial row is never a stage-1 current candidate.
        if row.get("source") != "Fugle paid bulk snapshot":
            reason = "NO_FUGLE_SNAPSHOT"
        elif row.get("snapshot_source_date") != checked_at.date().isoformat():
            reason = "NON_CURRENT_SNAPSHOT_DATE"
        elif row.get("snapshot_is_trial") is True:
            reason = "TRIAL_QUOTE"
        elif price is None:
            reason = "NO_OBSERVED_PRICE"
        elif price >= max_price:
            reason = "PRICE_NOT_BELOW_LIMIT"
        elif volume is None:
            reason = "NO_REPORTED_VOLUME"
        else:
            reason = None
        if reason:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        selected.append({
            "symbol": symbol, "name": row.get("name") or "",
            "exchange": exchange, "observed_price": price,
            "reported_volume_raw": volume,
            "volume_unit_verified": False,
            "change_pct_observed": row.get("change_pct"),
            "snapshot_date": row["snapshot_source_date"],
            "snapshot_observed_at": row.get("snapshot_observed_at"),
            "last_trade_time": row.get("last_trade_time"),
            "executed_trade_verified": row.get("data_status") == "FRESH_EXECUTED_TRADE",
            "candidate_scope": "STAGE1_OBSERVATION_ONLY",
            "classification": "A",
            "action": "等待",
            "production_eligible": False,
        })
        markets[exchange]["candidates"] += 1
    # Deterministic presentation without pretending raw volume proves liquidity.
    selected.sort(key=lambda x: (-x["reported_volume_raw"], x["symbol"]))
    return {
        "schema": SCHEMA,
        "checked_at_tpe": checked_at.isoformat(),
        "source": "FUGLE_PAID_SNAPSHOT",
        "universe_count": len(rows),
        "candidate_count": len(selected),
        "max_price_exclusive_twd": max_price,
        "by_exchange": markets,
        "excluded_reasons": reasons,
        "volume_unit_verified": False,
        "presentation_order": "REPORTED_RAW_VOLUME_DESC_NOT_LIQUIDITY_CERTIFIED",
        "candidates": selected,
        "production_eligible": False,
        "automatic_order": False,
        "trade_decision": "🔴 禁止新進場、未驗證通過",
    }
