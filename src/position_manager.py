from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict


PMS_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class PositionDecision:
    schema_version: str
    symbol: str
    state: str
    action: str
    reason: str
    last: float | None
    cost: float | None
    effective_stop: float | None
    target: float | None
    add_price: float | None
    add_allowed: bool
    stop_widening_rejected: bool
    thesis_valid: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _f(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _near(current, level, pct):
    if current is None or level is None or level == 0:
        return False
    return abs(current - level) / abs(level) <= pct


def evaluate_position(candidate: Dict[str, Any], near_pct: float = 0.006) -> PositionDecision:
    """Canonical long-side PMS position management.

    Hard rules:
    - stop may only move in the risk-reducing direction;
    - no averaging down / losing-position add;
    - add requires an explicit confirmed add signal;
    - PMS never invents a stop, target, or add price.
    """
    c = candidate or {}
    symbol = str(c.get("symbol") or "")
    last = _f(c.get("last", c.get("fugle_close")))
    cost = _f(c.get("cost", c.get("entry_price", c.get("entry"))))
    initial_stop = _f(c.get("initial_stop"))
    requested_stop = _f(c.get("stop"))
    trailing_stop = _f(c.get("trailing_stop"))
    target = _f(c.get("target", c.get("target1")))
    add_price = _f(c.get("add_price"))

    stop_candidates = [x for x in (initial_stop, requested_stop, trailing_stop) if x is not None]
    effective_stop = max(stop_candidates) if stop_candidates else None

    stop_widening_rejected = bool(
        initial_stop is not None
        and requested_stop is not None
        and requested_stop < initial_stop
    )

    risk_status = (c.get("risk") or {}).get("status")
    thesis_invalid = bool(c.get("thesis_invalid") or c.get("trade_thesis_invalid"))
    add_signal_confirmed = bool(c.get("add_signal_confirmed"))

    state = "HOLDING"
    action = "續抱"
    reason = "交易假設未失效"
    thesis_valid = not thesis_invalid

    if last is None:
        state, action, reason = "DATA_REQUIRED", "觀察", "缺少最新有效價格"
    elif thesis_invalid:
        state, action, reason = "EXIT", "退出", "交易假設已失效"
    elif effective_stop is not None and last <= effective_stop:
        state, action, reason = "STOP", "停損", "價格已觸及或跌破有效停損"
        thesis_valid = False
    elif target is not None and last >= target:
        state, action, reason = "TAKE_PROFIT", "減碼", "價格已觸及第一目標"
    elif effective_stop is not None and _near(last, effective_stop, near_pct):
        state, action, reason = "NEAR_STOP", "續抱", "價格接近有效停損，需提高警戒"
    elif target is not None and _near(last, target, near_pct):
        state, action, reason = "NEAR_TARGET", "續抱", "價格接近第一目標"
    else:
        profitable_or_flat = cost is None or last >= cost
        add_price_reached = add_price is None or last >= add_price
        add_allowed = bool(
            add_signal_confirmed
            and profitable_or_flat
            and add_price_reached
            and risk_status in (None, "ALLOW")
        )
        if add_allowed:
            state, action, reason = "ADD_READY", "加碼", "原部位非虧損且第二加碼訊號已確認"

    profitable_or_flat = (
        last is not None and (cost is None or last >= cost)
    )
    add_price_reached = (
        last is not None and (add_price is None or last >= add_price)
    )
    add_allowed = bool(
        state not in {"STOP", "EXIT", "DATA_REQUIRED"}
        and add_signal_confirmed
        and profitable_or_flat
        and add_price_reached
        and risk_status in (None, "ALLOW")
    )

    if stop_widening_rejected:
        reason += "；偵測到停損放寬要求，已拒絕並維持較嚴格停損"

    if add_signal_confirmed and last is not None and cost is not None and last < cost:
        reason += "；部位仍為虧損，禁止向下攤平加碼"
        add_allowed = False
        if state == "ADD_READY":
            state, action = "HOLDING", "續抱"

    return PositionDecision(
        schema_version=PMS_SCHEMA_VERSION,
        symbol=symbol,
        state=state,
        action=action,
        reason=reason,
        last=last,
        cost=cost,
        effective_stop=effective_stop,
        target=target,
        add_price=add_price,
        add_allowed=add_allowed,
        stop_widening_rejected=stop_widening_rejected,
        thesis_valid=thesis_valid,
    )
