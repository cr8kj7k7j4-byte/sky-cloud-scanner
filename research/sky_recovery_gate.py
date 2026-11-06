"""Fail-closed, read-only recovery acceptance. Never grants trading permission."""
import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


def _timestamp_ok(raw):
    if not isinstance(raw, str):
        return False
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _fresh_timestamp(raw, now, max_age_hours=36):
    if not _timestamp_ok(raw):
        return False
    timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    age = now - timestamp
    return timedelta(minutes=-5) <= age <= timedelta(hours=max_age_hours)


def evaluate(status, health=None, validation=None, *, now=None):
    status, health, validation = status or {}, health or {}, validation or {}
    w4 = status.get("w4_dashboard") or {}
    integrity = w4.get("strategy_evidence_integrity") or {}
    source = w4.get("forward_trade_provenance") or {}
    samples = (w4.get("sample_sufficiency") or {}).get("observed") or {}
    eligible = int(integrity.get("eligible_strategy_records") or 0)
    complete = int(integrity.get("complete_strategy_outcomes_with_modelled_costs") or 0)
    reasons = []
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone aware")
    status_time = status.get("generated_at_utc")
    if not _timestamp_ok(status_time):
        reasons.append("STATUS_TIMESTAMP_MISSING_OR_INVALID")
    elif not _fresh_timestamp(status_time, now):
        reasons.append("STATUS_STALE_OR_FUTURE")
    # Published diagnostics are a separate evidence layer. A green health
    # verdict is invalid when its published snapshot cannot be dated.
    if health.get("decision") == "HEALTH_FULLY_CERTIFIED":
        health_time = health.get("published_at_utc")
        if not _fresh_timestamp(health_time, now):
            reasons.append("HEALTH_STATUS_STALE_OR_UNDATED")
    if (validation.get("evidence") or {}).get("after_cost_expectancy_r") is not None:
        if not _fresh_timestamp(validation.get("published_at_utc"), now):
            reasons.append("MODEL_VALIDATION_STALE_OR_UNDATED")
    if health.get("decision") != "HEALTH_FULLY_CERTIFIED":
        reasons.append("LIVE_MARKET_NOT_CERTIFIED")
    if not (source.get("authoritative_forward_rule_source_verified") is True
            and source.get("can_certify_strategy_trades") is True):
        reasons.append("AUTHORITATIVE_STRATEGY_PROVENANCE_BLOCKED")
    if eligible < 200:
        reasons.append("STRATEGY_TRADE_SAMPLE_INSUFFICIENT")
    if int(samples.get("trading_days") or 0) < 20:
        reasons.append("FORWARD_TRADING_DAYS_INSUFFICIENT")
    if int(samples.get("regime_count") or 0) < 2:
        reasons.append("VERIFIED_MARKET_REGIMES_INSUFFICIENT")
    if eligible <= 0 or complete / eligible < 0.95:
        reasons.append("STRATEGY_OUTCOMES_INCOMPLETE")
    if samples.get("top_symbol_share") is None or float(samples["top_symbol_share"]) > .20:
        reasons.append("SYMBOL_CONCENTRATION_UNVERIFIED_OR_EXCESS")
    if int(integrity.get("observed_execution_fills") or 0) <= 0:
        reasons.append("EXECUTION_FILL_EVIDENCE_MISSING")
    expectancy = (validation.get("evidence") or {}).get("after_cost_expectancy_r")
    if expectancy is None:
        reasons.append("AFTER_COST_EXPECTANCY_UNVERIFIED")
    else:
        try:
            import math
            value = float(expectancy)
            if not math.isfinite(value) or value <= 0:
                reasons.append("AFTER_COST_EXPECTANCY_NOT_POSITIVE")
        except (ValueError, TypeError):
            reasons.append("AFTER_COST_EXPECTANCY_INVALID")
    return {
        "schema": "SKY_RECOVERY_ACCEPTANCE_V1",
        "audit_completed": True,
        "audit_timestamp_utc": now.astimezone(timezone.utc).isoformat(),
        "readiness": "BLOCKED" if reasons else "READY_FOR_W0_P0G_REVIEW_ONLY",
        "trade_authorized": False,
        "production_promoted": False,
        "reasons": reasons,
        "source_generated_at_utc": status.get("generated_at_utc"),
        "counts": {"ranking_observations": int(samples.get("samples") or 0),
                   "eligible_strategy_trades": eligible,
                   "complete_strategy_outcomes": complete,
                   "observed_execution_fills": int(integrity.get("observed_execution_fills") or 0),
                   "forward_days": int(samples.get("trading_days") or 0)},
        "note": "CI success confirms this audit ran, not live-data or strategy eligibility; W0/P0-G approval still required."
    }


def load(path):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--status", default="docs/SKY_EXTERNAL_LATEST_STATUS.json")
    p.add_argument("--health", default="docs/SKY_UNIFIED_LATEST_SYSTEM_HEALTH.json")
    p.add_argument("--validation", default="docs/SKY_UNIFIED_LATEST_MODEL_VALIDATION.json")
    p.add_argument("--out", default="output/recovery/acceptance.json")
    a = p.parse_args()
    result = evaluate(load(a.status), load(a.health), load(a.validation))
    dest = Path(a.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
