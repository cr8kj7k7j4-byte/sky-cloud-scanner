from dataclasses import dataclass, asdict
import math

from .execution_engine import ExecutionCostPolicy, evaluate_execution_rr, execution_gate


@dataclass(frozen=True)
class RiskPolicy:
    risk_per_trade_pct: float = 0.005
    daily_loss_limit_pct: float = 0.015
    max_portfolio_heat_pct: float = 0.03
    max_position_pct: float = 0.20
    correlation_limit_pct: float = 0.02
    max_concurrent_positions: int = 3
    stop_after_consecutive_losses: int = 2
    caution_loss_streak: int = 3
    defensive_loss_streak: int = 5
    lockdown_drawdown_pct: float = 0.06
    lot_size: int = 1000

    def to_dict(self):
        return asdict(self)


def _non_negative(value):
    return max(0.0, float(value or 0.0))


def drawdown_state(drawdown_pct=0.0, consecutive_losses=0, policy=None):
    policy = policy or RiskPolicy()
    dd = _non_negative(drawdown_pct)
    losses = max(0, int(consecutive_losses or 0))

    if dd >= policy.lockdown_drawdown_pct:
        return "LOCKDOWN"
    if losses >= policy.defensive_loss_streak:
        return "DEFENSIVE"
    if losses >= policy.caution_loss_streak:
        return "CAUTION"
    return "NORMAL"


def effective_risk_per_trade_pct(state, policy=None):
    policy = policy or RiskPolicy()
    if state == "LOCKDOWN":
        return 0.0
    if state == "DEFENSIVE":
        return policy.risk_per_trade_pct * 0.40
    if state == "CAUTION":
        return policy.risk_per_trade_pct * 0.70
    return policy.risk_per_trade_pct


def position_size(entry, stop, account_equity, state="NORMAL", policy=None):
    policy = policy or RiskPolicy()
    entry = float(entry)
    stop = float(stop)
    equity = _non_negative(account_equity)

    if equity <= 0 or entry <= 0:
        return 0
    per_share_risk = abs(entry - stop)
    if per_share_risk <= 0:
        return 0

    risk_budget = equity * effective_risk_per_trade_pct(state, policy)
    max_notional = equity * policy.max_position_pct
    by_risk = math.floor(risk_budget / per_share_risk)
    by_notional = math.floor(max_notional / entry)
    raw = min(by_risk, by_notional)

    lot = max(1, int(policy.lot_size))
    return max(0, (raw // lot) * lot)


def evaluate_trade(
    *,
    entry,
    stop,
    target,
    account_equity,
    daily_pnl=0.0,
    open_risk=0.0,
    concurrent_positions=0,
    correlated_open_risk=0.0,
    drawdown_pct=0.0,
    consecutive_losses=0,
    grade=None,
    policy=None,
    execution_policy=None,
):
    policy = policy or RiskPolicy()
    reasons = []
    required = []

    for name, value in (("entry", entry), ("stop", stop), ("target", target)):
        if value is None:
            required.append(name)

    equity = _non_negative(account_equity)
    if equity <= 0:
        required.append("account_equity")

    state = drawdown_state(drawdown_pct, consecutive_losses, policy)

    if required:
        return {
            "status": "RISK_INPUT_REQUIRED",
            "portfolio_allowed": False,
            "state": state,
            "required_inputs": required,
            "reasons": ["缺少正式風控輸入，不得轉為可進場訊號"],
            "recommended_shares": 0,
            "risk_budget": 0.0,
            "remaining_daily_risk_budget": 0.0,
            "remaining_portfolio_heat": 0.0,
            "net_rr": None,
            "gross_rr": None,
            "fee_tax_adjusted_rr": None,
            "execution_adjusted_rr": None,
            "execution_status": "EXECUTION_INPUT_REQUIRED",
        }

    entry = float(entry)
    stop = float(stop)
    target = float(target)
    if entry <= 0 or stop <= 0 or target <= 0:
        reasons.append("價格輸入必須大於 0")

    unit_risk = abs(entry - stop)
    reward = target - entry
    gross_rr = reward / unit_risk if unit_risk > 0 else None
    if unit_risk <= 0:
        reasons.append("Entry 與 Stop 不可相同")
    if stop >= entry:
        reasons.append("做多停損必須低於買進價")
    if reward <= 0:
        reasons.append("Long 模式 Target 必須高於 Entry")

    if state == "LOCKDOWN":
        reasons.append("回撤達 LOCKDOWN 門檻，禁止新開倉")
    if int(consecutive_losses or 0) >= policy.stop_after_consecutive_losses:
        reasons.append("連續兩筆停損，停止新進場")
    if state == "DEFENSIVE" and grade not in (None, "A+"):
        reasons.append("DEFENSIVE 僅允許 A+ 候選")

    daily_loss_used = max(0.0, -float(daily_pnl or 0.0))
    daily_limit = equity * policy.daily_loss_limit_pct
    remaining_daily = max(0.0, daily_limit - daily_loss_used)
    if remaining_daily <= 0:
        reasons.append("已達 Daily Loss Limit")

    open_risk = _non_negative(open_risk)
    heat_limit = equity * policy.max_portfolio_heat_pct
    remaining_heat = max(0.0, heat_limit - open_risk)
    if remaining_heat <= 0:
        reasons.append("已達 Max Portfolio Heat")

    if int(concurrent_positions or 0) >= policy.max_concurrent_positions:
        reasons.append("已達 Max Concurrent Positions")

    correlated_open_risk = _non_negative(correlated_open_risk)
    correlation_limit = equity * policy.correlation_limit_pct
    if correlated_open_risk >= correlation_limit:
        reasons.append("高度相關標的曝險已達 Correlation Limit")

    shares = position_size(entry, stop, equity, state, policy)
    unit_risk = abs(entry - stop)
    proposed_risk = shares * unit_risk
    base_risk_budget = equity * effective_risk_per_trade_pct(state, policy)
    executable_budget = min(base_risk_budget, remaining_daily, remaining_heat)

    if shares <= 0:
        reasons.append("風險預算不足以建立最小交易單位")
    elif proposed_risk > executable_budget + 1e-9:
        max_shares = math.floor(executable_budget / unit_risk) if unit_risk else 0
        lot = max(1, int(policy.lot_size))
        shares = max(0, (max_shares // lot) * lot)
        proposed_risk = shares * unit_risk
        if shares <= 0:
            reasons.append("剩餘風險預算不足以建立最小交易單位")

    allowed = not reasons
    result = {
        "status": "ALLOW" if allowed else "BLOCK",
        "portfolio_allowed": allowed,
        "state": state,
        "required_inputs": [],
        "reasons": reasons,
        "recommended_shares": shares if allowed else 0,
        "proposed_risk": round(proposed_risk if allowed else 0.0, 2),
        "proposed_risk_pct": round((proposed_risk / equity) if allowed and equity else 0.0, 6),
        "risk_budget": round(base_risk_budget, 2),
        "remaining_daily_risk_budget": round(remaining_daily, 2),
        "remaining_portfolio_heat": round(remaining_heat, 2),
        # Backward compatibility only: historical net_rr was actually gross RR.
        "net_rr": round(gross_rr, 3) if gross_rr is not None else None,
        "gross_rr": round(gross_rr, 3) if gross_rr is not None else None,
        "fee_tax_adjusted_rr": None,
        "execution_adjusted_rr": None,
        "execution_status": "EXECUTION_INPUT_REQUIRED",
    }

    if unit_risk > 0 and reward > 0 and execution_policy is not None:
        ex = evaluate_execution_rr(
            entry=entry,
            stop=stop,
            target=target,
            policy=execution_policy,
        )
        result["fee_tax_adjusted_rr"] = ex.get("fee_tax_adjusted_rr")
        result["execution_adjusted_rr"] = ex.get("execution_adjusted_rr")
        result["execution_status"] = ex.get("status")
        result["execution"] = ex
        exec_allowed, exec_reason = execution_gate(ex)
        result["execution_gate_reason"] = exec_reason
        if not exec_allowed:
            result["status"] = "BLOCK"
            result["portfolio_allowed"] = False
            result["recommended_shares"] = 0
            result["reasons"] = list(result["reasons"]) + [exec_reason]
    return result


def evaluate_candidate(candidate, portfolio_context, policy=None):
    """Fail closed for candidate admission when live account state is unknown.

    These fields MUST be reconciled from the actual position / trade ledger.
    A synthetic zero or environment default is not evidence of reconciliation.
    The upstream caller must supply metadata showing provenance and freshness.
    This is an admission gate, not a broker integration or an order placer.
    """
    policy = policy or RiskPolicy()
    candidate = candidate or {}
    portfolio_context = portfolio_context or {}
    required = (
        "account_equity", "daily_pnl", "open_risk",
        "concurrent_positions", "correlated_open_risk",
        "drawdown_pct", "consecutive_losses",
    )
    absent = [key for key in required if portfolio_context.get(key) is None]
    # Do not accept an unsigned / stale / research-only context as live truth.
    if portfolio_context.get("ledger_verified") is not True:
        absent.append("ledger_verified")
    if not portfolio_context.get("ledger_asof"):
        absent.append("ledger_asof")
    if not portfolio_context.get("ledger_source"):
        absent.append("ledger_source")
    if portfolio_context.get("ledger_fresh") is not True:
        absent.append("ledger_fresh")
    if portfolio_context.get("ledger_complete") is not True:
        absent.append("ledger_complete")
    if portfolio_context.get("execution_policy") is None:
        absent.append("execution_policy")
    if absent:
        return {
            "status": "RISK_INPUT_REQUIRED",
            "portfolio_allowed": False,
            "required_inputs": sorted(set(absent)),
            "reasons": ["實際持倉、損益或成本證據不完整，禁止新進場"],
            "recommended_shares": 0,
            "net_rr": None,
            "gross_rr": None,
            "fee_tax_adjusted_rr": None,
            "execution_adjusted_rr": None,
            "execution_status": "EXECUTION_INPUT_REQUIRED",
        }

    # Full execution-cost inputs are mandatory for new candidate admission.
    execution_policy = portfolio_context["execution_policy"]
    if not getattr(execution_policy, "enforce_gate", False):
        return {
            "status": "BLOCK",
            "portfolio_allowed": False,
            "required_inputs": ["execution_policy.enforce_gate"],
            "reasons": ["成本後風險報酬閘門未啟用，禁止新進場"],
            "recommended_shares": 0,
            "execution_status": "EXECUTION_GATE_DISABLED",
        }

    return evaluate_trade(
        entry=candidate.get("entry", candidate.get("last")),
        stop=candidate.get("stop"),
        target=candidate.get("target"),
        account_equity=portfolio_context["account_equity"],
        daily_pnl=portfolio_context["daily_pnl"],
        open_risk=portfolio_context["open_risk"],
        concurrent_positions=portfolio_context["concurrent_positions"],
        correlated_open_risk=portfolio_context["correlated_open_risk"],
        drawdown_pct=portfolio_context["drawdown_pct"],
        consecutive_losses=portfolio_context["consecutive_losses"],
        grade=candidate.get("grade"),
        policy=policy,
        execution_policy=execution_policy,
    )
