"""Fail-closed liquidity/quote quality review and canonical P0-C read-only handoff.

Provider total.tradeVolume is preserved as raw provider units: it is NOT treated
as Taiwan round lots without independent unit certification. A review passing
microstructure checks is not automatically a trading strategy recommendation.
"""
from __future__ import annotations

import math

from src.decision_engine import evaluate_decision
from src.config import MIN_TRADE_VALUE


def number(v):
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
        return f if math.isfinite(f) and f > 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def best(levels):
    if not isinstance(levels, list) or not levels or not isinstance(levels[0], dict):
        return None, None
    return number(levels[0].get("price")), number(levels[0].get("size"))


def review(quote, *, verified_trade=False, change_pct=None, volume_unit_verified=False):
    """Diagnostic quality gates; NO P0-C thresholds modified or bypassed."""
    if not isinstance(quote, dict):
        quote = {}
    bid, bid_size = best(quote.get("bids"))
    ask, ask_size = best(quote.get("asks"))
    spread = round((ask - bid) / ((ask + bid) / 2) * 100, 4) if bid and ask and ask >= bid else None
    total = quote.get("total") if isinstance(quote.get("total"), dict) else {}
    raw_volume = number(total.get("tradeVolume"))
    turnover_twd = number(total.get("tradeValue"))
    avg = number(quote.get("avgPrice"))
    # Research-only consistency check; not an official unit certification.
    implied_scale = turnover_twd / (raw_volume * avg) if turnover_twd and raw_volume and avg else None
    volume_scale_consistent_1000 = implied_scale is not None and 980 <= implied_scale <= 1020
    lasttrade = quote.get("lastTrade") if isinstance(quote.get("lastTrade"), dict) else {}
    last = number(lasttrade.get("price"))
    avg_distance = round((last / avg - 1) * 100, 3) if last and avg else None
    flags = []
    if not verified_trade:
        flags.append("MISSING_FRESH_EXECUTION")
    if bid is None or ask is None or spread is None:
        flags.append("MISSING_VALID_L1_SPREAD")
    elif spread > 0.8:  # P0-C first_gate spread value; research never relaxes it
        flags.append("SPREAD_GT_P0C_0_8_PCT")
    if bid_size is None or ask_size is None:
        flags.append("MISSING_L1_DEPTH")
    if raw_volume is None:
        flags.append("MISSING_PROVIDER_VOLUME")
    if turnover_twd is None:
        flags.append("MISSING_PROVIDER_TURNOVER_TWD")
    elif turnover_twd < MIN_TRADE_VALUE:
        flags.append("TURNOVER_BELOW_UNCHANGED_P0C_MIN")
    if not volume_unit_verified:
        flags.append("PROVIDER_VOLUME_UNIT_UNCERTIFIED")
    if avg_distance is None:
        flags.append("MISSING_AVERAGE_PRICE_DISTANCE")
    if change_pct is None:
        flags.append("UNKNOWN_CHASE_RISK")
    elif float(change_pct) >= 6:
        flags.append("RAPID_RISE_REQUIRES_ANTI_CHASE_REVIEW")
    return {
        "bid": bid, "ask": ask, "bid_size_raw": bid_size,
        "ask_size_raw": ask_size, "spread_pct": spread,
        "total_trade_volume_raw": raw_volume,
        "total_trade_value_twd": turnover_twd,
        "min_trade_value_twd": MIN_TRADE_VALUE,
        "turnover_gate_pass": turnover_twd is not None and turnover_twd >= MIN_TRADE_VALUE,
        "volume_unit_verified": bool(volume_unit_verified),
        "accounting_implied_volume_scale": round(implied_scale, 4) if implied_scale else None,
        "volume_scale_consistent_with_1000_shares_per_lot": volume_scale_consistent_1000,
        "provider_unit_contract_verified": False,
        "average_price": avg,
        "average_price_distance_pct": avg_distance,
        "reported_change_pct": change_pct,
        "quality_reasons": flags,
        "liquidity_certified": False,  # turnover alone cannot certify fill/capacity
        "l1_spread_gate_pass": spread is not None and spread <= 0.8,
        "decision_ready": False,
        "production_eligible": False,
    }


def canonical_read_only(symbol, quality, *, model_inputs=None):
    """Invoke the unchanged, canonical P0-C; don't synthesize P0-R or P0-K evidence."""
    model_inputs = model_inputs or {}
    # Never infer a BUY by fabricating missing P0-R, P0-K, or strategy fields.
    data = {
        "symbol": str(symbol),
        "flags": ["X:未通過全市場正式行情驗證"] if not model_inputs.get("whole_market_certified") else [],
        "risk": {"status": "RISK_INPUT_REQUIRED"},
        "evidence_ledger": {"decision_eligible": False, "items": []},
        "strategy_plan": {"production_eligible": False},
        "classification_cap": "X",
    }
    result = evaluate_decision(data).to_dict()
    result["upstream_quality_reasons"] = quality.get("quality_reasons", [])
    result["model_readiness"] = {
        "v14_gate_contract_invoked": True,
        "p0_r_risk_inputs_complete": False,
        "p0_k_evidence_eligible": False,
        "five_minute_candles_verified": False,
        "vwap_source_verified": False,
        "breakout_quality_verified": False,
        "execution_cost_inputs_complete": False,
        "whole_market_certified": bool(model_inputs.get("whole_market_certified", False)),
        "final_full_rule_v14_validation": False,
    }
    result["live_execution_allowed"] = False
    return result
