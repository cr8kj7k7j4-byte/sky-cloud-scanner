"""Read-only audit of current Sky P0-R configuration vs confirmed safety contract.

This audit intentionally exercises synthetic test prices, NOT trading signals.
It never modifies Production, reads any real holdings, or submits orders.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src import config
from src.cost_profiles import USER_CASH_DAYTRADE_20261022
from src.risk_engine import RiskPolicy, evaluate_trade

OUT = Path("output/sky_p0r_policy_drift")
EXPECTED = {
    "account_equity_twd": 500000,
    "risk_per_trade_twd": 5000,
    "max_position_twd": 100000,
    "max_positions": 3,
    "portfolio_risk_twd": 15000,
    "daily_loss_stop_twd": 10000,
    "consecutive_loss_stop": 2,
    "min_cost_after_rr": 1.5,
}


def audit():
    """Compare source configuration AND real Risk Engine decisions, fail closed."""
    equity = config.ACCOUNT_EQUITY
    policy = RiskPolicy(
        risk_per_trade_pct=config.RISK_PER_TRADE_PCT,
        daily_loss_limit_pct=config.DAILY_LOSS_LIMIT_PCT,
        max_portfolio_heat_pct=config.MAX_PORTFOLIO_HEAT_PCT,
        max_position_pct=config.MAX_POSITION_PCT,
        correlation_limit_pct=config.CORRELATION_LIMIT_PCT,
        max_concurrent_positions=config.MAX_CONCURRENT_POSITIONS,
        caution_loss_streak=config.CAUTION_LOSS_STREAK,
        defensive_loss_streak=config.DEFENSIVE_LOSS_STREAK,
        lockdown_drawdown_pct=config.LOCKDOWN_DRAWDOWN_PCT,
        lot_size=config.LOT_SIZE,
    )
    cost = USER_CASH_DAYTRADE_20261022.to_execution_policy(
        min_execution_rr=config.EXEC_MIN_RR,
        enforce_gate=config.EXEC_ENFORCE_GATE,
        # Deliberately do not manufacture slippage, spread or fill probability.
    )
    fixture = {"entry": 50, "stop": 49, "target": 52, "account_equity": equity,
               "grade": "A+", "policy": policy, "execution_policy": cost}
    two_losses = evaluate_trade(**fixture, consecutive_losses=2)
    daily_limit = evaluate_trade(**fixture, daily_pnl=-EXPECTED["daily_loss_stop_twd"])
    # Force enforcement for this diagnostic: missing inputs may never be treated as zero.
    from dataclasses import replace
    without_execution = evaluate_trade(**{**fixture, "execution_policy": replace(cost, enforce_gate=True)})
    checks = [
        {"name": "capital_500k", "passed": equity == EXPECTED["account_equity_twd"],
         "observed": equity},
        {"name": "single_trade_risk_5k",
         "passed": round(equity * policy.risk_per_trade_pct, 2) == EXPECTED["risk_per_trade_twd"],
         "observed": round(equity * policy.risk_per_trade_pct, 2)},
        {"name": "single_stock_cap_100k",
         "passed": round(equity * policy.max_position_pct, 2) == EXPECTED["max_position_twd"],
         "observed": round(equity * policy.max_position_pct, 2)},
        {"name": "max_three_positions",
         "passed": policy.max_concurrent_positions == EXPECTED["max_positions"],
         "observed": policy.max_concurrent_positions},
        {"name": "portfolio_risk_cap_15k",
         "passed": round(equity * policy.max_portfolio_heat_pct, 2) == EXPECTED["portfolio_risk_twd"],
         "observed": round(equity * policy.max_portfolio_heat_pct, 2)},
        {"name": "daily_stop_at_10k",
         "passed": daily_limit.get("status") == "BLOCK" and not daily_limit.get("portfolio_allowed"),
         "observed": daily_limit.get("status")},
        {"name": "two_consecutive_losses_stop",
         "passed": two_losses.get("status") == "BLOCK" and not two_losses.get("portfolio_allowed"),
         "observed": two_losses.get("status")},
        {"name": "missing_execution_inputs_block",
         "passed": (without_execution.get("status") == "BLOCK"
                    and without_execution.get("execution_status") == "EXECUTION_INPUT_REQUIRED"),
         "observed": {
             "risk": without_execution.get("status"),
             "execution": without_execution.get("execution_status"),
             "enforce_execution_gate": config.EXEC_ENFORCE_GATE,
         }},
        {"name": "runtime_cost_gate_enabled",
         "passed": config.EXEC_ENFORCE_GATE is True,
         "observed": config.EXEC_ENFORCE_GATE},
        {"name": "cost_after_rr_threshold",
         "passed": cost.min_execution_rr >= EXPECTED["min_cost_after_rr"],
         "observed": cost.min_execution_rr},
    ]
    defects = [x["name"] for x in checks if not x["passed"]]
    return {
        "schema": "SKY_P0R_POLICY_RUNTIME_DRIFT_RESEARCH_V1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "PAPER_ONLY_SYNTHETIC_DIAGNOSTIC",
        "source_config": "src/config.py",
        "source_engine": "src/risk_engine.py",
        "source_cost": "src/cost_profiles.py",
        "expected": EXPECTED,
        "checks": checks,
        "mismatch_count": len(defects),
        "mismatches": defects,
        "paper_ledger_verified": False,
        "broker_account_required_for_research": False,
        "current_portfolio_ledger_verified": False,  # Legacy field: do not use as a research gate
        "realized_daily_pnl_verified": False,
        "real_slippage_and_fill_verified": False,
        "official_v14_full_rule_evidence_verified": False,
        "risk_production_eligible": False,
        "automatic_order": False,
        "verdict": "CONFIG_AND_EVIDENCE_BLOCKED" if defects else "PAPER_LEDGER_AND_EXECUTION_EVIDENCE_REQUIRED",
        "trade_action": "禁止交易",
        "note": "測試使用虛構價格；ALLOW 僅表示風控函式在該模擬輸入下可能放行，絕非真實可交易訊號。",
    }


def main():
    result = audit()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    lines = [
        "# Sky P0-R 正式設定與執行行為差異（只讀驗收）",
        "",
        "**🔴 禁止真實交易；Paper 模擬帳本與成交證據尚待驗證。**",
        "",
        "| 項目 | 檢查 | 實際觀察 |",
        "| --- | --- | --- |",
    ]
    for item in result["checks"]:
        lines.append(f'| {item["name"]} | {"符合" if item["passed"] else "不符"} | {item["observed"]} |')
    lines += ["", "差異數：" + str(result["mismatch_count"]),
              "研究驗收不需要券商開戶；Paper 模擬持倉、停損及成本證據仍待驗證。",
              "不得以模擬通過、測試成功或風控預設值作為正式買進資格。", ""]
    (OUT / "latest.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
