"""Read-only research evidence bridge for paid Fugle full-market observations.

This module is intentionally separate from P0-C/P0-R production decisions.
Scores are deterministic observational evidence (never win probabilities).
Price levels are shown ONLY when the scanner supplies a real strategy_plan;
they are never reverse-engineered from a daily high/low or fabricated.
"""
from __future__ import annotations

import math
from src.sky_mobile_table import evidence_scores, direction_label


def positive(value):
    if isinstance(value, bool):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) and n > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def observation_evidence(item):
    """Score only same-session Fugle paid observations with OHLC context."""
    if item.get("source") != "Fugle paid bulk snapshot":
        return {"status": "SOURCE_NOT_FUGLE", "bull": None, "bear": None}
    if item.get("data_status") in (
        "SNAPSHOT_DATE_NOT_TODAY", "MISSING_QUOTE", "MISSING_EXECUTED_PRICE",
        "TRIAL_QUOTE", "FUTURE_EXECUTION_TIME",
    ):
        return {"status": "INVALID_SESSION_OR_PRICE", "bull": None, "bear": None}
    last = positive(item.get("last_price"))
    op = positive(item.get("open_price"))
    hi = positive(item.get("high_price"))
    lo = positive(item.get("low_price"))
    change = item.get("change_pct")
    # Do not rely on a standalone price plus change_pct alone: OHLC must exist.
    if last is None or op is None or hi is None or lo is None or not lo <= last <= hi:
        return {"status": "INSUFFICIENT_FUGLE_OHLC", "bull": None, "bear": None}
    scored = {"last": last, "open": op, "high": hi, "low": lo,
              "change_pct": change}
    bull, bear = evidence_scores(scored)
    return {"status": "RESEARCH_ONLY_UNVERIFIED_MODEL",
            "bull": bull, "bear": bear,
            "direction": direction_label(bull, bear, {}),
            "source": item["source"], "data_time": item.get("last_trade_time"),
            "data_status": item.get("data_status"),
            "score_version": "SKY_OBSERVATIONAL_EVIDENCE_V1"}


def scanner_plans(scanner):
    """Use only already-computed, symbol-matched research plans in scan artifact."""
    out = {}
    if not isinstance(scanner, dict):
        return out
    for key in ("deep", "deep_rejected", "deep_unverified"):
        for row in scanner.get(key, []) or []:
            if not isinstance(row, dict):
                continue
            code = str(row.get("symbol") or "")
            plan = row.get("strategy_plan")
            if not code or not isinstance(plan, dict):
                continue
            values = [positive(plan.get(k)) for k in ("trigger", "max_entry", "stop", "target")]
            if any(x is None for x in values):
                continue
            trigger, max_entry, stop, target = values
            if not (stop < trigger <= max_entry < target):
                continue
            out[code] = {"trigger": trigger, "max_entry": max_entry,
                         "stop": stop, "target": target,
                         "strategy_version": row.get("strategy_version"),
                         "research_only": True}
    return out
