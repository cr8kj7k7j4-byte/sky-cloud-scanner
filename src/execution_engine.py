from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class ExecutionCostPolicy:
    """
    P0-X research cost assumptions.

    Missing values are represented by None. Zero is a valid explicit
    assumption and must not be confused with missing data.
    """
    buy_commission_rate: Optional[float] = None
    sell_commission_rate: Optional[float] = None
    sell_tax_rate: Optional[float] = None
    entry_slippage_bps: Optional[float] = None
    exit_slippage_bps: Optional[float] = None
    spread_bps: Optional[float] = None
    liquidity_penalty_bps: Optional[float] = None
    fill_probability: Optional[float] = None
    financing_interest_per_share: Optional[float] = None
    require_financing_interest: bool = False
    min_execution_rr: float = 1.5
    enforce_gate: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


_REQUIRED_EXECUTION_FIELDS = (
    "buy_commission_rate",
    "sell_commission_rate",
    "sell_tax_rate",
    "entry_slippage_bps",
    "exit_slippage_bps",
    "spread_bps",
    "liquidity_penalty_bps",
)


def _missing(policy: ExecutionCostPolicy) -> list[str]:
    missing = [
        name
        for name in _REQUIRED_EXECUTION_FIELDS
        if getattr(policy, name) is None
    ]
    if policy.require_financing_interest and policy.financing_interest_per_share is None:
        missing.append("financing_interest_per_share")
    return missing


def _bps(value: float) -> float:
    return float(value) / 10000.0


def _validate_long_prices(entry: float, stop: float, target: float) -> None:
    if entry <= 0 or stop <= 0 or target <= 0:
        raise ValueError("entry/stop/target must be positive")
    if stop >= entry:
        raise ValueError("long stop must be below entry")
    if target <= entry:
        raise ValueError("long target must be above entry")


def evaluate_execution_rr(
    *,
    entry: float,
    stop: float,
    target: float,
    policy: ExecutionCostPolicy | None = None,
) -> dict:
    """
    Compute three RR layers for a long trade:

    1) gross_rr
       Pure price geometry, no costs.

    2) fee_tax_adjusted_rr
       Commissions + sell-side tax only. Returned only when those three
       explicit assumptions are available.

    3) execution_adjusted_rr
       Commissions + sell-side tax + adverse slippage + half-spread on each
       side + liquidity penalty. Returned only when every required execution
       input is explicit.

    fill_adjusted_expected_rr is a research heuristic:
       execution_adjusted_rr * fill_probability

    It is NOT a statistical expectancy and is never called a win rate.
    """
    policy = policy or ExecutionCostPolicy()
    entry = float(entry)
    stop = float(stop)
    target = float(target)
    _validate_long_prices(entry, stop, target)

    gross_risk = entry - stop
    gross_reward = target - entry
    gross_rr = gross_reward / gross_risk

    result = {
        "status": "EXECUTION_INPUT_REQUIRED",
        "gross_rr": round(gross_rr, 4),
        "fee_tax_adjusted_rr": None,
        "execution_adjusted_rr": None,
        "fill_adjusted_expected_rr": None,
        "cost_drag_rr": None,
        "gate_pass": None,
        "gate_enforced": bool(policy.enforce_gate),
        "min_execution_rr": float(policy.min_execution_rr),
        "missing_inputs": _missing(policy),
        "assumptions": policy.to_dict(),
        "components": {},
    }

    fee_fields = (
        policy.buy_commission_rate,
        policy.sell_commission_rate,
        policy.sell_tax_rate,
    )
    if all(v is not None for v in fee_fields):
        buy_fee = entry * float(policy.buy_commission_rate)
        target_sell_fee = target * float(policy.sell_commission_rate)
        target_tax = target * float(policy.sell_tax_rate)
        stop_sell_fee = stop * float(policy.sell_commission_rate)
        stop_tax = stop * float(policy.sell_tax_rate)

        net_reward_fee_tax = (
            target - entry - buy_fee - target_sell_fee - target_tax
        )
        net_risk_fee_tax = (
            entry - stop + buy_fee + stop_sell_fee + stop_tax
        )
        fee_tax_rr = (
            net_reward_fee_tax / net_risk_fee_tax
            if net_risk_fee_tax > 0 else None
        )
        result["fee_tax_adjusted_rr"] = (
            round(fee_tax_rr, 4) if fee_tax_rr is not None else None
        )
        result["components"].update(
            {
                "buy_fee_per_share": round(buy_fee, 6),
                "target_sell_fee_per_share": round(target_sell_fee, 6),
                "target_tax_per_share": round(target_tax, 6),
                "stop_sell_fee_per_share": round(stop_sell_fee, 6),
                "stop_tax_per_share": round(stop_tax, 6),
            }
        )

    if result["missing_inputs"]:
        return result

    spread_half = float(policy.spread_bps) / 2.0
    entry_impact_bps = (
        float(policy.entry_slippage_bps)
        + spread_half
        + float(policy.liquidity_penalty_bps)
    )
    exit_impact_bps = (
        float(policy.exit_slippage_bps)
        + spread_half
        + float(policy.liquidity_penalty_bps)
    )

    effective_entry = entry * (1.0 + _bps(entry_impact_bps))
    effective_target_exit = target * (1.0 - _bps(exit_impact_bps))
    effective_stop_exit = stop * (1.0 - _bps(exit_impact_bps))

    buy_fee = effective_entry * float(policy.buy_commission_rate)
    target_sell_fee = effective_target_exit * float(policy.sell_commission_rate)
    target_tax = effective_target_exit * float(policy.sell_tax_rate)
    stop_sell_fee = effective_stop_exit * float(policy.sell_commission_rate)
    stop_tax = effective_stop_exit * float(policy.sell_tax_rate)

    financing_interest = float(policy.financing_interest_per_share or 0.0)

    execution_reward = (
        effective_target_exit
        - effective_entry
        - buy_fee
        - target_sell_fee
        - target_tax
        - financing_interest
    )
    execution_risk = (
        effective_entry
        - effective_stop_exit
        + buy_fee
        + stop_sell_fee
        + stop_tax
        + financing_interest
    )

    execution_rr = (
        execution_reward / execution_risk
        if execution_risk > 0 else None
    )

    fill_p = policy.fill_probability
    if fill_p is not None:
        fill_p = min(1.0, max(0.0, float(fill_p)))

    fill_adjusted = (
        execution_rr * fill_p
        if execution_rr is not None and fill_p is not None
        else None
    )

    gate_pass = (
        execution_rr is not None
        and execution_rr >= float(policy.min_execution_rr)
    )

    result.update(
        {
            "status": "COMPLETE",
            "execution_adjusted_rr": round(execution_rr, 4)
            if execution_rr is not None else None,
            "fill_adjusted_expected_rr": round(fill_adjusted, 4)
            if fill_adjusted is not None else None,
            "cost_drag_rr": round(gross_rr - execution_rr, 4)
            if execution_rr is not None else None,
            "gate_pass": gate_pass,
            "components": {
                **result["components"],
                "effective_entry": round(effective_entry, 6),
                "effective_target_exit": round(effective_target_exit, 6),
                "effective_stop_exit": round(effective_stop_exit, 6),
                "entry_impact_bps": round(entry_impact_bps, 4),
                "exit_impact_bps": round(exit_impact_bps, 4),
                "execution_reward_per_share": round(execution_reward, 6),
                "execution_risk_per_share": round(execution_risk, 6),
                "financing_interest_per_share": round(financing_interest, 6),
            },
        }
    )
    return result


def execution_gate(result: dict) -> tuple[bool, str]:
    """
    Gate is enforced only when:
    - policy says enforce_gate=True, and
    - execution inputs are complete.

    Missing assumptions never silently become zero-cost assumptions.
    """
    if not result.get("gate_enforced"):
        return True, "EXECUTION_GATE_DISABLED"
    if result.get("status") != "COMPLETE":
        return False, "EXECUTION_INPUT_REQUIRED"
    if not result.get("gate_pass"):
        return False, "EXECUTION_RR_BELOW_MINIMUM"
    return True, "EXECUTION_RR_OK"
