"""Sky MCR V1.0: preregistered, fail-closed, research-only trade decision.

Only explicit point-in-time inputs are accepted. No API access or order routing.
The output "RESEARCH_READY" is NEVER an instruction to trade.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, time
from math import floor, isfinite
from typing import Optional
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")
COST_PRIMARY = .0045
COST_STRESS = .0065

@dataclass(frozen=True)
class Input:
    symbol: str
    observed_at: datetime
    price: float
    prev_trading_date: date
    margin_data_date: date
    margin_ratio: float
    margin_balance_lots: float
    previous_close: float
    vwap: float
    bid: float
    ask: float
    volume_ratio_1m: float
    forced_selloff_observed: bool
    seller_exhaustion_confirmed: bool
    consecutive_buy_snapshots: bool
    market_gate_ok: bool
    phase: str
    breakout_level: float
    retest_low: float
    resistance_1: float
    resistance_2: float
    data_fresh_seconds: float
    is_daytrade_eligible: bool
    is_price_limit_locked: bool
    available_cash: float
    portfolio_open_risk: float
    open_positions: int
    daily_net_pnl: float
    consecutive_stops: int
    execution_cost_covered: bool = False

@dataclass(frozen=True)
class Decision:
    state: str
    reasons: tuple[str, ...]
    entry: Optional[float] = None
    max_acceptable: Optional[float] = None
    stop: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    rr_primary: Optional[float] = None
    rr_stress: Optional[float] = None
    quantity_shares: int = 0
    research_only: bool = True

def net_rr(entry: float, stop: float, target: float, round_trip_cost: float) -> float:
    """Conservative half-spread cost allocation, round-trip total as input."""
    entry_paid = entry * (1 + round_trip_cost / 2)
    stop_net = stop * (1 - round_trip_cost / 2)
    target_net = target * (1 - round_trip_cost / 2)
    risk = entry_paid - stop_net
    return (target_net - entry_paid) / risk if risk > 0 else float("-inf")

def decide(x: Input) -> Decision:
    block, wait = [], []
    def valid(v):
        return isinstance(v, (int, float)) and isfinite(v)
    values = (x.price, x.margin_ratio, x.margin_balance_lots, x.previous_close, x.vwap,
              x.bid, x.ask, x.volume_ratio_1m, x.breakout_level, x.retest_low,
              x.resistance_1, x.resistance_2, x.data_fresh_seconds,
              x.available_cash, x.portfolio_open_risk, x.daily_net_pnl)
    if not all(valid(v) for v in values):
        return Decision("禁止交易", ("INVALID_OR_MISSING_NUMERIC_DATA",))
    if x.observed_at.tzinfo is None:
        return Decision("禁止交易", ("MISSING_OBSERVATION_TIMEZONE",))
    now = x.observed_at.astimezone(TZ)
    if now.date().weekday() >= 5 or not (time(9, 10) <= now.time() <= time(12, 45)):
        block.append("OUTSIDE_ENTRY_WINDOW")
    if x.margin_data_date != x.prev_trading_date or x.margin_data_date >= now.date():
        block.append("NON_PIT_MARGIN_DATE")
    if not (0 < x.margin_ratio < 130 and x.margin_balance_lots >= 100):
        block.append("OUTSIDE_MARGIN_UNIVERSE")
    if not (0 < x.price < 100 and x.previous_close > 0):
        block.append("PRICE_OUT_OF_RANGE")
    if not x.is_daytrade_eligible or x.is_price_limit_locked:
        block.append("INELIGIBLE_OR_PRICE_LIMIT")
    if x.data_fresh_seconds < 0 or x.data_fresh_seconds > 35:
        block.append("STALE_QUOTE")
    if not (0 < x.bid <= x.ask and (x.ask-x.bid)/x.price <= .005):
        block.append("SPREAD_INVALID_OR_TOO_WIDE")
    if not x.execution_cost_covered:
        block.append("EXECUTION_QUALITY_NOT_VERIFIED")
    if x.consecutive_stops >= 2 or x.daily_net_pnl <= -10000:
        block.append("DAILY_KILL_SWITCH")
    if x.open_positions >= 3 or x.portfolio_open_risk >= 15000 or x.available_cash <= 0:
        block.append("PORTFOLIO_LIMIT")
    if not x.market_gate_ok:
        block.append("MARKET_GATE_FAILED")
    if x.phase not in {"P3", "P4"}:
        wait.append("UNFAVORABLE_PHASE")
    if not x.forced_selloff_observed or not x.seller_exhaustion_confirmed:
        wait.append("CAPITULATION_NOT_CONFIRMED")
    if not x.consecutive_buy_snapshots or x.volume_ratio_1m < 1.3:
        wait.append("BUY_PRESSURE_NOT_CONFIRMED")
    if not (x.price > x.vwap and x.price > x.breakout_level):
        wait.append("BREAKOUT_NOT_CONFIRMED")
    if not (0 < x.breakout_level and (x.price/x.breakout_level-1) <= .004):
        block.append("CHASE_TOO_FAR")
    if x.price / x.previous_close - 1 > .07:
        block.append("EXTENDED_FROM_PREV_CLOSE")
    if not (0 < x.retest_low < x.price):
        block.append("INVALID_STRUCTURAL_STOP")
    else:
        if (x.price - x.retest_low)/x.price > .02:
            block.append("STOP_TOO_FAR")
    if not (x.price < x.resistance_1 < x.resistance_2):
        block.append("MISSING_TWO_OBSERVED_RESISTANCES")
    if block:
        return Decision("禁止交易", tuple(block + wait))
    if wait:
        return Decision("等待", tuple(wait))
    rr1 = net_rr(x.price, x.retest_low, x.resistance_1, COST_PRIMARY)
    rr2 = net_rr(x.price, x.retest_low, x.resistance_2, COST_STRESS)
    if rr1 < 1.5 or rr2 < 2.0:
        return Decision("等待", ("COST_AFTER_RR_INSUFFICIENT",), rr_primary=rr1, rr_stress=rr2)
    # Worst-case stop risk: primary cost assumption; capital and portfolio headroom.
    risk_per_share = x.price*(1+COST_PRIMARY/2)-x.retest_low*(1-COST_PRIMARY/2)
    risk_budget = min(5000, max(0, 15000-x.portfolio_open_risk))
    shares = min(floor(risk_budget/risk_per_share), floor(100000/x.price), floor(x.available_cash/x.price))
    shares = (shares // 1000) * 1000
    if shares < 1000:
        return Decision("禁止交易", ("CAPITAL_INSUFFICIENT_FOR_ONE_LOT",))
    return Decision("RESEARCH_READY", ("ALL_PRE_REGISTERED_GATES_PASS",),
                    entry=x.price, max_acceptable=x.breakout_level*1.004,
                    stop=x.retest_low, target_1=x.resistance_1,
                    target_2=x.resistance_2, rr_primary=rr1,
                    rr_stress=rr2, quantity_shares=shares)
