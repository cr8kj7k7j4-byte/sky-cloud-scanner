"""Sky v1.4 Stage5 independent, read-only breakout/anti-chase evidence veto.

Never derives trading triggers/targets from archived P0-S 5m breakout,
nor converts incomplete 5m/quote observations into A+ or order permission.
"""
from __future__ import annotations

from datetime import datetime
import math


def _num(v):
    if isinstance(v, bool):
        return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _time(v):
    if not isinstance(v, str):
        return None
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return dt if dt.utcoffset() is not None else None
    except ValueError:
        return None


def audit(candidate, quote, candle):
    """Report each missing causal or microstructure prerequisite explicitly.

    Existing P0-C upper spread 0.8% is only a diagnostic veto here; this module
    does NOT tune strategy thresholds or claim a statistically validated trigger.
    """
    candidate = candidate if isinstance(candidate, dict) else {}
    quote = quote if isinstance(quote, dict) else {}
    candle = candle if isinstance(candle, dict) else {}
    micro = quote.get("microstructure")
    micro = micro if isinstance(micro, dict) else {}
    price = _num(quote.get("verified_trade_price"))
    last_time = _time(quote.get("last_trade_time"))
    spread = _num(micro.get("spread_pct"))
    bid = _num(micro.get("bid"))
    ask = _num(micro.get("ask"))
    volume = _num(micro.get("total_trade_volume_raw"))
    turnover = _num(micro.get("total_trade_value_twd"))
    reasons = []
    if quote.get("executed_trade_verified") is not True or quote.get("status") != "FRESH_EXECUTED_TRADE" or last_time is None:
        reasons.append("UNVERIFIED_LAST_EXECUTED_TRADE")
    if price is None or not 0 < price < 100:
        reasons.append("EXECUTED_PRICE_OUTSIDE_USER_DAYTRADE_LIMIT")
    if bid is None or ask is None or bid <= 0 or ask <= 0 or ask < bid or spread is None:
        reasons.append("L1_SPREAD_PROVENANCE_MISSING_OR_INVALID")
    elif spread > 0.8:
        reasons.append("SPREAD_EXCEEDS_CANONICAL_0_8_PCT")
    if volume is None or volume <= 0 or turnover is None or turnover <= 0:
        reasons.append("PROVIDER_LIQUIDITY_EVIDENCE_MISSING")
    if micro.get("volume_unit_verified") is not True or micro.get("liquidity_certified") is not True:
        reasons.append("VOLUME_UNIT_OR_EXECUTABLE_LIQUIDITY_NOT_CERTIFIED")
    change_pct = _num(candidate.get("change_pct_observed"))
    if change_pct is None:
        reasons.append("ANTI_CHASE_CHANGE_PCT_UNKNOWN")
    # Anti-chase hold: a rising observation is NOT itself a valid breakout.
    # 6% is existing Stage2 diagnostic hold, not a retuned production rule.
    elif change_pct >= 6:
        reasons.append("RAPID_RISE_DIAGNOSTIC_HOLD")
    if candle.get("status") != "CANDLE_TICKER_RESEARCH_READY_NOT_TRADE":
        reasons.append("5M_TICKER_NOT_READY")
    if candle.get("bar_timestamp_semantics_certified") is not True or candle.get("bar_sequence_valid") is not True:
        reasons.append("5M_CAUSAL_AVAILABILITY_NOT_CERTIFIED")
    flags = ("is_disposition", "is_attention", "is_specific_abnormal")
    if any(candle.get(f) is not False for f in flags):
        reasons.append("UNVERIFIED_OR_RESTRICTED_SECURITY_FLAG")
    features = candle.get("feature_preview")
    features = features if isinstance(features, dict) else {}
    volume_ratio = _num(features.get("volume_ratio"))
    relative_strength = _num(features.get("relative_strength"))
    if volume_ratio is None:
        reasons.append("MULTIPERIOD_VOLUME_EVIDENCE_MISSING")
    if relative_strength is None:
        reasons.append("MARKET_RELATIVE_STRENGTH_MISSING")
    # A proper trade setup needs approved trigger, prior bar high/low,
    # entry/stop invalidation, confirmed VWAP, and execution evidence.
    reasons.extend((
        "OFFICIAL_VWAP_CAUSALITY_NOT_CERTIFIED",
        "CANONICAL_BREAKOUT_PRIOR_COMPLETED_BARS_NOT_VERIFIED",
        "BREAKOUT_TRIGGER_AND_FAILURE_NOT_VERIFIED",
        "AFTER_COST_RR_NOT_VERIFIED",
        "P0_R_AND_P0_K_CURRENT_LEDGER_NOT_VERIFIED",
        "W0_P0_G_FORMAL_VALIDATION_REQUIRED",
    ))
    return {
        "schema": "SKY_STAGE5_BREAKOUT_ANTI_CHASE_EVIDENCE_V1",
        "symbol": str(quote.get("symbol") or candidate.get("symbol") or ""),
        "exchange": str(quote.get("exchange") or candidate.get("exchange") or ""),
        "observation_change_pct": change_pct,
        "last_verified_trade_price": price if quote.get("executed_trade_verified") is True else None,
        "spread_pct": spread,
        "observed_5m_volume_ratio": volume_ratio,
        "observed_relative_strength": relative_strength,
        "reasons": list(dict.fromkeys(reasons)),
        "breakout_quality_certified": False,
        "anti_chase_full_rule_certified": False,
        "trade_trigger_certified": False,
        "price_entry": None, "price_stop": None, "price_target": None,
        "production_eligible": False, "a_plus": False,
        "action": "禁止交易",
    }
