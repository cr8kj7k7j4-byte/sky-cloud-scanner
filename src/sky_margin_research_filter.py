"""SKY維持率: deterministic, source-attributed *research* filter.

Consumes externally supplied rows, NEVER fetches market data, certifies trades,
or grants buy eligibility. The caller must supply the full TWSE/TPEx universe.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

SCHEMA = "SKY_MARGIN_OBSERVATION_V1"
LIMITS = {"ratio_lt": "120", "capital_twd_lt": "3000000000",
          "previous_volume_lots_gt": "100", "price_twd_lt": "100"}
FIELDS = ("margin_ratio_pct", "paid_in_capital_twd", "previous_volume_lots",
          "last_trade_price_twd")


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return number if number.is_finite() and number >= 0 else None


def _date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def filter_margin_observations(
    rows: Sequence[Mapping[str, Any]], *,
    observation_date: str, previous_session_date: str,
    universe_total: int, universe_source: str,
) -> dict[str, Any]:
    """Strict four-factor screening; missing evidence is rejected, not estimated.

    Required per row: symbol, exchange (TWSE/TPEx), four numeric fields,
    ratio_source, ratio_date, capital_source, capital_date, volume_source,
    volume_date, price_source, price_date, price_evidence (EXECUTED_TRADE).
    Ratio provenance is disclosed, NOT an independent provider-entitlement gate.
    Returns only research observations and no trade trigger, score or quantity.
    """
    if not _date(observation_date) or not _date(previous_session_date):
        raise ValueError("INVALID_SESSION_DATE")
    if previous_session_date >= observation_date:
        raise ValueError("SESSION_ORDER_INVALID")
    if not isinstance(universe_total, int) or isinstance(universe_total, bool) or universe_total < 1:
        raise ValueError("INVALID_FULL_UNIVERSE_TOTAL")
    if not isinstance(universe_source, str) or not universe_source.strip():
        raise ValueError("MISSING_UNIVERSE_SOURCE")
    if not isinstance(rows, (list, tuple)) or len(rows) > universe_total:
        raise ValueError("INVALID_UNIVERSE_ROWS")

    selected, rejected, seen = [], [], set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("INVALID_UNIVERSE_ROW")
        symbol = str(row.get("symbol") or "").strip()
        market = row.get("exchange")
        if not symbol.isdigit() or not 4 <= len(symbol) <= 6 or market not in ("TWSE", "TPEx"):
            raise ValueError("INVALID_SYMBOL_OR_MARKET")
        if symbol in seen:
            raise ValueError("DUPLICATE_UNIVERSE_SYMBOL")
        seen.add(symbol)
        reasons = []
        values = {key: _decimal(row.get(key)) for key in FIELDS}
        if any(x is None for x in values.values()):
            reasons.append("MISSING_OR_INVALID_NUMERIC_INPUT")
        for prefix, date_field, upper_date in (
            ("ratio", "ratio_date", previous_session_date),
            ("capital", "capital_date", observation_date),
            ("volume", "volume_date", previous_session_date),
            ("price", "price_date", observation_date),
        ):
            source = row.get(prefix + "_source")
            when = row.get(date_field)
            if not isinstance(source, str) or not source.strip():
                reasons.append("MISSING_" + prefix.upper() + "_SOURCE")
            if not _date(when) or when > upper_date:
                reasons.append("INVALID_" + prefix.upper() + "_DATE")
        if row.get("ratio_date") != previous_session_date:
            reasons.append("RATIO_NOT_PREVIOUS_SESSION")
        if row.get("volume_date") != previous_session_date:
            reasons.append("VOLUME_NOT_PREVIOUS_SESSION")
        if row.get("price_date") not in (observation_date, previous_session_date):
            reasons.append("PRICE_SESSION_UNMATCHED")
        if row.get("price_evidence") != "EXECUTED_TRADE":
            reasons.append("NO_AUTHENTICATED_EXECUTED_TRADE")
        if not reasons:
            if not (values["margin_ratio_pct"] < 120
                    and values["paid_in_capital_twd"] < 3_000_000_000
                    and values["previous_volume_lots"] > 100
                    and values["last_trade_price_twd"] < 100):
                reasons.append("FOUR_FACTOR_SCREEN_FAILED")
        if reasons:
            rejected.append({"symbol": symbol, "reasons": reasons})
            continue
        selected.append({
            "symbol": symbol, "exchange": market,
            "margin_ratio_pct": str(values["margin_ratio_pct"]),
            "paid_in_capital_twd": str(values["paid_in_capital_twd"]),
            "previous_volume_lots": str(values["previous_volume_lots"]),
            "last_trade_price_twd": str(values["last_trade_price_twd"]),
            "ratio_estimate_source": row["ratio_source"],
            "ratio_estimate_date": row["ratio_date"],
            "ratio_method": row.get("ratio_method") or "UNSPECIFIED_ESTIMATE_METHOD",
            "price_source": row["price_source"], "price_date": row["price_date"],
            "action": "觀察", "buy_eligible": False,
        })
    selected.sort(key=lambda x: (Decimal(x["margin_ratio_pct"]),
                                 -Decimal(x["previous_volume_lots"]), x["symbol"]))
    coverage_complete = len(rows) == universe_total
    return {
        "schema": SCHEMA, "mode": "OBSERVATION_ONLY",
        "observation_date": observation_date,
        "previous_session_date": previous_session_date,
        "universe_source": universe_source,
        "universe_total": universe_total,
        "rows_received": len(rows), "coverage_complete": coverage_complete,
        "watchlist_is_universe": False,
        "screened_count": len(selected), "rejected_count": len(rejected),
        "candidates": selected[:10] if coverage_complete else [],
        "rejections": rejected,
        "status": "RESEARCH_ONLY" if coverage_complete else "HOLD_INCOMPLETE_UNIVERSE",
        "trade_status": "NO_TRADE",
        "buy_eligible": False,
        "reason": "No verified margin live runner / strategy / A2 / P0-R / mobile E2E",
    }
