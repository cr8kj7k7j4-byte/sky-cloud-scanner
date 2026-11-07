"""Fail-closed full-universe margin rebound watchlist and sorting contract.

This is a research observation feed, NEVER an instruction to trade.
Expected value is accepted only when independent audited evidence is explicitly supplied.
"""
from __future__ import annotations
from datetime import datetime
from math import isfinite

SORT_MODES = ("verified_ev", "volume", "reversal")
MIN_SAMPLE = 200

def _number(value):
    try:
        v = float(value)
        return v if isfinite(v) else None
    except (TypeError, ValueError):
        return None

def _verified_ev(evidence, symbol):
    """Reject unverified, proxy, in-sample and insufficient forward evidence."""
    x = (evidence or {}).get(symbol)
    if not isinstance(x, dict):
        return None
    if x.get("verification") != "PASS" or x.get("point_in_time") is not True:
        return None
    if x.get("costs_included") is not True or x.get("out_of_sample") is not True:
        return None
    if x.get("forward_trading_days", 0) < 20 or x.get("independent_trades", 0) < MIN_SAMPLE:
        return None
    if x.get("market_regimes", 0) < 2 or x.get("data_completeness_pct", 0) < 95:
        return None
    if x.get("max_symbol_concentration_pct", 101) > 20:
        return None
    return _number(x.get("net_expectancy_per_trade_pct"))

def build_watchlist(universe, snapshots=(), evidence=None, sort_by="verified_ev",
                    observed_at=None, page=1, page_size=50):
    """Display ALL qualifying symbols via paginated rows; no top-N truncation.

    universe: {symbol: FinMind prior-session margin row}, already filtered below 130%.
    snapshots: current-session quote snapshots; absent/stale quotes remain marked unavailable.
    """
    if sort_by not in SORT_MODES:
        raise ValueError("Unsupported sort mode")
    if not isinstance(page, int) or page < 1 or not isinstance(page_size, int) or not 1 <= page_size <= 200:
        raise ValueError("Invalid page")
    latest = {}
    for quote in snapshots:
        sid = str(quote.get("stock_id", ""))
        if sid not in universe:
            continue
        stamp = str(quote.get("date", ""))
        if sid not in latest or stamp > str(latest[sid].get("date", "")):
            latest[sid] = quote
    rows = []
    for sid, margin in universe.items():
        quote = latest.get(sid, {})
        px = _number(quote.get("close"))
        volume = _number(quote.get("total_volume"))
        ratio = _number(margin.get("margin_maintenance"))
        if ratio is None or not 0 < ratio < 130:
            continue
        ev = _verified_ev(evidence, str(sid))
        # A snapshot is NOT a verified continuous tape or an executable trigger.
        rows.append({
            "stock_id": str(sid),
            "stock_name": str(margin.get("stock_name") or quote.get("stock_name") or ""),
            "margin_data_date": margin.get("date"),
            "estimated_margin_maintenance_pct": ratio,
            "margin_balance_lots": _number(margin.get("margin_balance")),
            "last_snapshot_price": px if px is not None and px > 0 else None,
            "last_snapshot_volume": volume if volume is not None and volume >= 0 else None,
            "snapshot_at": quote.get("date"),
            "quote_verified_live": False,
            "reversal_score": None,
            "net_expectancy_per_trade_pct": ev,
            "expectancy_verified": ev is not None,
            "action": "觀察",
            "trade_eligible": False,
            "status": "RESEARCH_ONLY",
        })
    if sort_by == "verified_ev":
        rows.sort(key=lambda x: (
            x["net_expectancy_per_trade_pct"] is None,
            -(x["net_expectancy_per_trade_pct"] or 0),
            -(x["last_snapshot_volume"] or 0),
            x["stock_id"],
        ))
    elif sort_by == "volume":
        rows.sort(key=lambda x: (-(x["last_snapshot_volume"] or 0), x["stock_id"]))
    else:
        # No unverified reversal scores are manufactured: fall back to liquidity.
        rows.sort(key=lambda x: (-(x["last_snapshot_volume"] or 0), x["stock_id"]))
    start = (page - 1) * page_size
    return {
        "model": "Sky 融資清洗反轉觀察",
        "mode": "RESEARCH_ONLY",
        "observed_at": observed_at,
        "sort_requested": sort_by,
        "sort_effective": "volume" if (sort_by == "reversal" or
            (sort_by == "verified_ev" and not any(r["expectancy_verified"] for r in rows))) else sort_by,
        "total": len(rows),
        "page": page,
        "page_size": page_size,
        "total_pages": (len(rows) + page_size - 1) // page_size,
        "rows": rows[start:start + page_size],
        "no_trade_without_validation": True,
        "source_note": "Estimated financing maintenance from prior session; snapshot != validated Fugle live quote.",
    }
