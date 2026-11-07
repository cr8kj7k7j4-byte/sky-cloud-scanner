"""Sky MCR V1.5 — research-only, point-in-time, fail-closed indicators.

Inputs MUST be previously released daily financing observations and timestamped
intraday observations. No network I/O, trading or notification in this module.
All outputs are observational and NEVER an authorized production buy signal.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite
from typing import Optional

MODEL = "Sky MCR V1.5"
STATUS = "INSUFFICIENT_DATA"
PRIMARY_COST = 0.0045
STRESS_COST = 0.0065


@dataclass(frozen=True)
class Financing:
    symbol: str
    trade_date: str
    published_at: str
    estimated_maintenance_pct: Optional[float] = None
    margin_balance: Optional[float] = None
    previous_margin_balance: Optional[float] = None
    margin_cost: Optional[float] = None


@dataclass(frozen=True)
class Tape:
    observed_at: str
    price: float
    volume: float
    aggressive_buy_volume: Optional[float] = None
    aggressive_sell_volume: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    vwap: Optional[float] = None
    prior_low: Optional[float] = None
    resistance: Optional[float] = None
    previous_sell_impact: Optional[float] = None
    current_sell_impact: Optional[float] = None
    market_gate: Optional[bool] = None
    event_risk_clear: Optional[bool] = None


@dataclass(frozen=True)
class Portfolio:
    equity: float = 500_000
    risk_per_trade: float = 5_000
    max_symbol_capital: float = 100_000
    max_open_positions: int = 3
    portfolio_risk_limit: float = 15_000
    max_daily_loss: float = 10_000
    daily_net_pnl: Optional[float] = None
    open_risk: Optional[float] = None
    open_positions: Optional[int] = None
    consecutive_losses: Optional[int] = None


def _time(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("timestamps must include UTC offset")
    return dt


def _valid(value: Optional[float], *, positive: bool = False) -> bool:
    return value is not None and isfinite(value) and (not positive or value > 0)


def classify(fin: Financing, tape: Tape, portfolio: Portfolio = Portfolio(),
             *, side: str = "LONG", entry: Optional[float] = None,
             stop: Optional[float] = None, target: Optional[float] = None) -> dict:
    """Returns research observations and gates; NEVER a live trade authorization."""
    failed: list[str] = []
    missing: list[str] = []
    features: dict = {}
    try:
        published, observed = _time(fin.published_at), _time(tape.observed_at)
        if published > observed:
            failed.append("LOOK_AHEAD_FINANCING")
        if fin.trade_date >= observed.date().isoformat():
            failed.append("SAME_DAY_FINANCING_NOT_ELIGIBLE")
    except (ValueError, TypeError):
        failed.append("INVALID_TIMESTAMP")
    if side not in ("LONG", "SHORT"):
        failed.append("UNSUPPORTED_SIDE")
    if side == "SHORT":
        failed.append("SHORT_BORROWABILITY_NOT_VERIFIED")

    for key in ("estimated_maintenance_pct", "margin_balance", "previous_margin_balance"):
        if not _valid(getattr(fin, key)):
            missing.append(key)
    if _valid(fin.margin_balance) and _valid(fin.previous_margin_balance, positive=True):
        features["margin_balance_change_pct"] = 100 * (
            fin.margin_balance / fin.previous_margin_balance - 1)
        features["deleveraging"] = features["margin_balance_change_pct"] < 0
    else:
        features["margin_balance_change_pct"] = None
        features["deleveraging"] = None
    features["estimated_below_130"] = (
        fin.estimated_maintenance_pct < 130
        if _valid(fin.estimated_maintenance_pct) else None)
    if _valid(fin.margin_cost, positive=True) and _valid(tape.price, positive=True):
        features["distance_from_margin_cost_pct"] = 100 * (tape.price / fin.margin_cost - 1)
    else:
        features["distance_from_margin_cost_pct"] = None

    if not _valid(tape.price, positive=True) or not _valid(tape.volume):
        failed.append("INVALID_MARKET_PRICE_OR_VOLUME")
    if not _valid(tape.aggressive_buy_volume) or not _valid(tape.aggressive_sell_volume):
        missing.append("AGGRESSOR_CLASSIFIED_TRADES")
        features["buy_share"] = None
    else:
        denominator = tape.aggressive_buy_volume + tape.aggressive_sell_volume
        if denominator <= 0:
            missing.append("NONZERO_AGGRESSOR_VOLUME")
            features["buy_share"] = None
        else:
            features["buy_share"] = tape.aggressive_buy_volume / denominator
    if _valid(tape.bid, positive=True) and _valid(tape.ask, positive=True) and tape.ask >= tape.bid:
        features["spread_pct"] = (tape.ask - tape.bid) / ((tape.ask + tape.bid) / 2) * 100
    else:
        features["spread_pct"] = None
        missing.append("VALID_BID_ASK")
    features["sell_impact_declining"] = (
        tape.current_sell_impact < tape.previous_sell_impact
        if _valid(tape.previous_sell_impact) and _valid(tape.current_sell_impact)
        else None
    )
    features["holds_prior_low"] = (
        tape.price >= tape.prior_low if _valid(tape.prior_low, positive=True) and _valid(tape.price, positive=True) else None
    )
    features["above_vwap"] = (
        tape.price > tape.vwap if _valid(tape.vwap, positive=True) and _valid(tape.price, positive=True) else None
    )
    features["above_resistance"] = (
        tape.price > tape.resistance if _valid(tape.resistance, positive=True) and _valid(tape.price, positive=True) else None
    )
    for key in ("sell_impact_declining", "holds_prior_low", "above_vwap", "above_resistance"):
        if features[key] is None:
            missing.append(key)

    if tape.market_gate is not True:
        (missing if tape.market_gate is None else failed).append("MARKET_GATE")
    if tape.event_risk_clear is not True:
        (missing if tape.event_risk_clear is None else failed).append("EVENT_RISK_REVIEW")
    if portfolio.daily_net_pnl is None or portfolio.open_risk is None or portfolio.open_positions is None or portfolio.consecutive_losses is None:
        missing.append("CURRENT_PORTFOLIO_STATE")
    else:
        if portfolio.daily_net_pnl <= -portfolio.max_daily_loss or portfolio.consecutive_losses >= 2:
            failed.append("DAILY_KILL_SWITCH")
        if portfolio.open_risk >= portfolio.portfolio_risk_limit:
            failed.append("PORTFOLIO_HEAT_LIMIT")
        if portfolio.open_positions >= portfolio.max_open_positions:
            failed.append("POSITION_COUNT_LIMIT")

    # RR is a hypothetical cost-stressed comparison, not an execution quote.
    if not all(_valid(v, positive=True) for v in (entry, stop, target)):
        missing.append("ENTRY_STOP_TARGET")
        features["rr_primary"] = None
        features["rr_stress"] = None
        features["max_research_shares"] = None
    elif side == "LONG" and not (stop < entry < target):
        failed.append("INVALID_LONG_PRICE_STRUCTURE")
    elif side == "LONG":
        risk = entry - stop
        for name, cost in (("rr_primary", PRIMARY_COST), ("rr_stress", STRESS_COST)):
            expected_cost = entry * cost
            features[name] = (target - entry - expected_cost) / (risk + expected_cost)
        features["max_research_shares"] = max(0, int(min(
            portfolio.risk_per_trade / risk, portfolio.max_symbol_capital / entry,
            max(0, portfolio.portfolio_risk_limit - (portfolio.open_risk or 0)) / risk)))
        if features["rr_primary"] < 1.5:
            failed.append("AFTER_COST_RR_BELOW_1_5")
    else:
        missing.append("SHORT_EXECUTION_COST_AND_BORROW")

    # Candidate thresholds are observational ONLY; never approved entry gates.
    features["research_reversal_pattern"] = all((
        features["estimated_below_130"] is True,
        features["deleveraging"] is True,
        features["sell_impact_declining"] is True,
        features["holds_prior_low"] is True,
        features["above_vwap"] is True,
        features["above_resistance"] is True,
        features["buy_share"] is not None and features["buy_share"] > .55,
    ))
    state = "X" if failed else "A_RESEARCH_ONLY" if not missing and features["research_reversal_pattern"] else "WATCH"
    return {
        "model": MODEL, "governance": STATUS, "production_signal": False,
        "action": "禁止交易" if failed else "觀察" if state == "WATCH" else "等待",
        "classification": state, "symbol": fin.symbol, "data_asof": tape.observed_at,
        "financing_published_at": fin.published_at,
        "estimate_is_not_broker_account_margin": True,
        "features": features, "missing": sorted(set(missing)),
        "failed": sorted(set(failed)),
        "note": "Research only. Not a buy order, probability, or verified positive expectancy.",
    }


def evaluate_payload(payload: dict) -> dict:
    return classify(
        Financing(**payload["financing"]), Tape(**payload["tape"]),
        Portfolio(**payload.get("portfolio", {})),
        side=payload.get("side", "LONG"),
        entry=payload.get("entry"), stop=payload.get("stop"), target=payload.get("target"),
    )


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="MCR research-only JSON evaluator")
    parser.add_argument("--input", required=True, help="Input JSON with financing and tape")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    result = evaluate_payload(data)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({"classification": result["classification"], "action": result["action"], "production_signal": False}, ensure_ascii=False))
