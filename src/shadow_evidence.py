from __future__ import annotations

from math import isfinite


def evaluate_shadow_pipeline_readiness(
    *,
    ledger_start: str,
    eligible_successful_scan_runs: int,
    paper_files: int,
    records_loaded: int,
) -> dict:
    """Classify Shadow evidence collection health without treating zero as failure.

    Zero eligible scans after ledger activation means collection has not started.
    Once an eligible scan exists, missing paper artifacts or records are pipeline
    failures and must fail closed.
    """
    scans = max(0, int(eligible_successful_scan_runs or 0))
    files = max(0, int(paper_files or 0))
    records = max(0, int(records_loaded or 0))

    if scans == 0:
        status = "WAITING_FOR_FIRST_ELIGIBLE_SCAN"
        healthy = True
        collection_started = False
        blockers = []
    elif files == 0:
        status = "PIPELINE_ARTIFACT_MISSING"
        healthy = False
        collection_started = True
        blockers = ["eligible_scan_exists_but_no_paper_artifact"]
    elif records == 0:
        status = "PIPELINE_RECORDS_MISSING"
        healthy = False
        collection_started = True
        blockers = ["paper_artifact_exists_but_no_records_loaded"]
    else:
        status = "COLLECTING"
        healthy = True
        collection_started = True
        blockers = []

    return {
        "status": status,
        "healthy": healthy,
        "collection_started": collection_started,
        "ledger_start": str(ledger_start or ""),
        "eligible_successful_scan_runs": scans,
        "paper_files": files,
        "records_loaded": records,
        "blocking_items": blockers,
        "note": (
            "Pipeline readiness only classifies evidence collection health. "
            "It does not imply strategy edge, profitability, or promotion readiness."
        ),
    }


def _finite(value):
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if isfinite(x) else None


def _max_drawdown_r(values):
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in values:
        equity += float(value)
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return round(max_dd, 6)


def evaluate_portfolio_cost_capacity_evidence(
    records,
    *,
    min_cost_complete_ratio: float = 0.95,
    max_symbol_share: float = 0.20,
    max_participation_rate: float | None = None,
) -> dict:
    """Fail-closed evidence contract for Shadow strategy outcomes.

    This function does not authorize production and does not invent capacity
    assumptions. Capacity remains NOT_EVALUABLE until an explicit participation
    limit is supplied and market trade-value observations exist.
    """
    rows = [dict(x) for x in (records or []) if isinstance(x, dict)]

    eligible = []
    complete = []
    participation_rates = []
    symbol_counts = {}

    for row in rows:
        outcome = dict(row.get("outcome") or {})
        strategy_outcome = dict(outcome.get("strategy_counterfactual") or {})
        status = str(strategy_outcome.get("status") or "").upper()

        if status and status != "NOT_ELIGIBLE":
            eligible.append(row)

        r_multiple = _finite(strategy_outcome.get("r_multiple"))
        if status == "COMPLETE" and r_multiple is not None:
            complete.append((row, r_multiple))
            symbol = str(row.get("symbol") or "")
            if symbol:
                symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1

            risk = dict(row.get("risk") or {})
            strategy = dict(row.get("strategy") or {})
            market = dict(row.get("market") or {})
            shares = _finite(risk.get("recommended_shares"))
            entry = _finite(strategy.get("trigger"))
            if entry is None:
                entry = _finite(market.get("last"))
            trade_value = _finite(market.get("trade_value"))
            if (
                shares is not None
                and shares > 0
                and entry is not None
                and entry > 0
                and trade_value is not None
                and trade_value > 0
            ):
                participation_rates.append((shares * entry) / trade_value)

    eligible_n = len(eligible)
    complete_n = len(complete)
    cost_complete_ratio = complete_n / eligible_n if eligible_n else 0.0

    rs = [r for _, r in complete]
    expectancy_r = sum(rs) / len(rs) if rs else None
    wins = sum(x for x in rs if x > 0)
    losses = abs(sum(x for x in rs if x < 0))
    profit_factor = (
        wins / losses
        if rs and losses > 0
        else (float("inf") if rs and wins > 0 else None)
    )
    top_symbol_count = max(symbol_counts.values()) if symbol_counts else 0
    top_symbol_share = top_symbol_count / complete_n if complete_n else 0.0

    capacity_threshold = (
        None if max_participation_rate is None else float(max_participation_rate)
    )
    capacity_evaluable = (
        capacity_threshold is not None and bool(participation_rates)
    )
    peak_participation = max(participation_rates) if participation_rates else None
    median_participation = None
    if participation_rates:
        vals = sorted(participation_rates)
        n = len(vals)
        mid = n // 2
        median_participation = (
            vals[mid]
            if n % 2
            else (vals[mid - 1] + vals[mid]) / 2.0
        )

    checks = {
        "has_complete_strategy_outcomes": complete_n > 0,
        "cost_completeness": (
            eligible_n > 0
            and cost_complete_ratio >= float(min_cost_complete_ratio)
        ),
        "symbol_concentration": (
            complete_n > 0 and top_symbol_share <= float(max_symbol_share)
        ),
        "capacity": (
            None
            if not capacity_evaluable
            else peak_participation <= capacity_threshold
        ),
    }

    if complete_n == 0:
        status = "NOT_EVALUABLE"
    elif checks["capacity"] is None:
        status = "CAPACITY_INPUT_REQUIRED"
    elif all(value is True for value in checks.values()):
        status = "EVIDENCE_READY"
    else:
        status = "EVIDENCE_INCOMPLETE"

    return {
        "status": status,
        "production_eligible": False,
        "checks": checks,
        "observed": {
            "records": len(rows),
            "eligible_strategy_records": eligible_n,
            "complete_strategy_outcomes": complete_n,
            "cost_complete_ratio": round(cost_complete_ratio, 6),
            "unique_symbols": len(symbol_counts),
            "top_symbol_share": round(top_symbol_share, 6),
            "expectancy_r": (
                None if expectancy_r is None else round(expectancy_r, 6)
            ),
            "profit_factor": (
                "inf"
                if profit_factor == float("inf")
                else None if profit_factor is None
                else round(profit_factor, 6)
            ),
            "max_drawdown_r": (
                None if not rs else _max_drawdown_r(rs)
            ),
            "capacity_observations": len(participation_rates),
            "median_participation_rate": (
                None
                if median_participation is None
                else round(median_participation, 8)
            ),
            "peak_participation_rate": (
                None
                if peak_participation is None
                else round(peak_participation, 8)
            ),
        },
        "thresholds": {
            "min_cost_complete_ratio": float(min_cost_complete_ratio),
            "max_symbol_share": float(max_symbol_share),
            "max_participation_rate": capacity_threshold,
        },
        "note": (
            "Portfolio/Cost/Capacity evidence is descriptive Shadow validation. "
            "No result here is a win rate, profit guarantee, or automatic "
            "Production promotion."
        ),
    }
