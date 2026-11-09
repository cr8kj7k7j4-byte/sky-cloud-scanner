"""Read-only observed-market visibility, independent from production trade eligibility.

The rows argument MUST contain only accepted same-session executed trades from
validate_whole_market_rows. No missing prices are inferred, and no model
training, scores, entries or trade permissions are manufactured here.
"""
from __future__ import annotations


def build_research_visibility(universe, accepted_rows, quote_audit, observed_at):
    valid = []
    for row in accepted_rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or "")
        if not symbol:
            continue
        valid.append({
            "symbol": symbol,
            "name": row.get("name"),
            "exchange": row.get("exchange"),
            "last": row.get("last"),
            "change_pct": row.get("change_pct"),
            "volume": row.get("volume"),
            "trade_time": row.get("trade_time") or row.get("last_trade_time")
                          or row.get("timestamp"),
            "source": row.get("source") or "TWSE_MIS_OPERATIONAL",
            "data_state": "ACCEPTED_EXECUTED_TRADE_BY_MARKET_GATE",
            "research_direction": None,
            "bull_score": None,
            "bear_score": None,
            "trigger": None,
            "stop": None,
            "target": None,
            "trade_eligible": False,
            "action": "觀察",
        })
    valid.sort(key=lambda x: x["symbol"])
    return {
        "schema": "SKY_MARKET_RESEARCH_VISIBILITY_V1",
        "observed_at_tpe": observed_at,
        "universe_count": len(universe),
        "accepted_count": len(valid),
        "not_verified_count": max(0, len(universe) - len(valid)),
        "quote_coverage_pct": round(100 * len(valid) / len(universe), 2) if universe else 0.0,
        "operational_full_market_verified": quote_audit.get("valid_whole_market_operational") is True,
        "data_scope": "OBSERVED_ACCEPTED_EXECUTED_TRADES_ONLY",
        "not_six_model_inference": True,
        "not_price_prediction": True,
        "production_signal": False,
        "order_authorized": False,
        "trading_decision": "禁止新進場、未驗證通過",
        "note": "Accepted observed prices remain visible even when the full-market trading gate blocks. Missing/unverified quotes are never invented.",
        "observations": valid,
    }
