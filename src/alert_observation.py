"""Display-only Sky 警戒 observations, independent of production qualification.

Only rows accepted by the actual executed-trade freshness validator enter this
report. This module never assigns A+, permits an order, or changes P0-C/P0-R.
"""
from datetime import datetime


def build_alert_observation(rows, universe, *, observed_at, limit=100):
    universe = list(universe or [])
    usable = []
    for row in rows or []:
        price = row.get("last")
        if not isinstance(price, (int, float)) or price <= 0:
            continue
        usable.append(row)
    twse_count = sum(r.get("exchange") == "TWSE" for r in usable)
    tpex_count = sum(r.get("exchange") == "TPEx" for r in usable)
    twse_total = sum(r.get("exchange") == "TWSE" for r in universe)
    tpex_total = sum(r.get("exchange") == "TPEx" for r in universe)
    ranked = sorted(usable, key=lambda r: (
        float(r.get("change_pct") or -999), float(r.get("trade_value") or 0)
    ), reverse=True)
    candidates = [{
        "symbol": r.get("symbol"), "name": r.get("name"),
        "exchange": r.get("exchange"), "last": r.get("last"),
        "change_pct": r.get("change_pct"), "volume": r.get("volume"),
        "trade_value": r.get("trade_value"),
        "open": r.get("open"), "high": r.get("high"), "low": r.get("low"),
        "bid": r.get("bid"), "ask": r.get("ask"),
        "quote_source": r.get("quote_source"),
        "quote_date": r.get("quote_date"),
        "quote_time": r.get("quote_time"),
        "last_trade_timestamp": r.get("last_trade_timestamp"),
        "classification": "UNVERIFIED_OBSERVATION",
        "now_action": "觀察",
        "production_entry_allowed": False,
    } for r in ranked[:max(0, limit)]]
    return {
        "mode": "OBSERVATION_ONLY_NOT_PRODUCTION",
        "generated_at": observed_at.isoformat() if isinstance(observed_at, datetime) else str(observed_at),
        "source_scope": "accepted_current_session_executed_trade_rows_only",
        "twse_valid": twse_count, "twse_universe": twse_total,
        "tpex_valid": tpex_count, "tpex_universe": tpex_total,
        "valid_total": len(usable), "universe_total": len(universe),
        "coverage_pct": round(100*len(usable)/len(universe), 2) if universe else 0,
        "candidate_count": len(candidates), "candidates": candidates,
        "warning": "🔴 禁止新進場、未驗證通過；觀察資訊不等於交易資格。資料不足一律保留缺值。",
    }
