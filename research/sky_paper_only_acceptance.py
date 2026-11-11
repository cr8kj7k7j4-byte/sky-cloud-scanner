"""PAPER_ONLY admission and cadence evidence audit. Never sends orders or claims fills.

Real market observations are evidence of prices, not execution. Broker accounts are
NOT a prerequisite for research/Paper; a broker ledger remains mandatory to enable
REAL_LIVE_TRADING in a future, separately governed implementation.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import json
import math
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")
RISK = {"equity_twd": 500000, "risk_per_trade_twd": 5000,
        "daily_loss_stop_twd": 10000, "single_stock_twd": 100000,
        "portfolio_heat_twd": 15000, "max_positions": 3,
        "consecutive_stop_limit": 2, "min_after_cost_rr": 1.5}


def paper_gate(paper_ledger, cost_evidence):
    """Synthetic/paper ONLY. Do not invoke the live risk engine or issue orders."""
    reasons = []
    if not isinstance(paper_ledger, dict) or paper_ledger.get("mode") != "PAPER_ONLY":
        reasons.append("PAPER_LEDGER_REQUIRED")
        paper_ledger = {}
    fields = ("daily_realized_net_pnl_twd", "consecutive_stops",
              "open_positions", "open_stop_risk_twd", "proposed_entry",
              "proposed_stop", "proposed_notional_twd")
    for field in fields:
        x = paper_ledger.get(field)
        if (not isinstance(x, (int, float)) or isinstance(x, bool)
                or not math.isfinite(x)):
            reasons.append("PAPER_INPUT_MISSING_" + field.upper())
    x = {key:paper_ledger.get(key) for key in fields}
    numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool)
                  and math.isfinite(v) for v in x.values())
    if numeric:
        if x["daily_realized_net_pnl_twd"] <= -RISK["daily_loss_stop_twd"]:
            reasons.append("DAILY_LOSS_STOP")
        if x["consecutive_stops"] >= RISK["consecutive_stop_limit"]:
            reasons.append("TWO_CONSECUTIVE_STOPS")
        if x["open_positions"] >= RISK["max_positions"]:
            reasons.append("MAX_POSITIONS")
        if x["open_stop_risk_twd"] >= RISK["portfolio_heat_twd"]:
            reasons.append("PORTFOLIO_HEAT_LIMIT")
        if x["proposed_notional_twd"] > RISK["single_stock_twd"]:
            reasons.append("SINGLE_STOCK_CAP")
        if x["proposed_entry"] <= x["proposed_stop"] or x["proposed_stop"] <= 0:
            reasons.append("INVALID_LONG_STOP_DIRECTION")
        elif x["proposed_notional_twd"] > 0:
            proposed_stop_risk = (x["proposed_notional_twd"] / x["proposed_entry"]
                                  * (x["proposed_entry"] - x["proposed_stop"]))
            if proposed_stop_risk > RISK["risk_per_trade_twd"]:
                reasons.append("SINGLE_TRADE_RISK_LIMIT")
            if x["open_stop_risk_twd"] + proposed_stop_risk > RISK["portfolio_heat_twd"]:
                reasons.append("PORTFOLIO_HEAT_LIMIT")
    if not isinstance(cost_evidence, dict) or cost_evidence.get("execution_cost_complete") is not True:
        reasons.append("FULL_EXECUTION_COST_MISSING")
    if not isinstance(cost_evidence, dict) or cost_evidence.get("after_cost_rr_certified") is not True:
        reasons.append("AFTER_COST_RR_NOT_CERTIFIED")
    elif not isinstance(cost_evidence.get("after_cost_rr"), (int, float)) or (
            not math.isfinite(cost_evidence["after_cost_rr"]) or
            cost_evidence["after_cost_rr"] < RISK["min_after_cost_rr"]):
        reasons.append("AFTER_COST_RR_BELOW_THRESHOLD")
    # Even a valid paper evaluation is only PAPER_ELIGIBLE, never real-trading authorization.
    return {"mode": "PAPER_ONLY", "paper_eligible": not reasons,
            "reasons": sorted(set(reasons)), "production_eligible": False,
            "live_order_enabled": False, "live_trade_action": "禁止交易"}


def cadence_slots():
    """09:00--13:30 TPE, inclusive: 55 intended *research* dispatch slots."""
    return [f"{h:02d}:{m:02d}" for h in range(9, 14)
            for m in range(0, 60, 5) if (h < 13 or m <= 30)]


def audit_status(status, *, paper_readback=None, signal_source=None, market_source=None):
    """Read actual Sky metadata; never infer scheduled cadence from on-demand run."""
    if not isinstance(status, dict):
        status = {}
    timestamp = status.get("data_timestamp")
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        valid_time = parsed.tzinfo is not None
    except (ValueError, TypeError, AttributeError):
        valid_time = False
    ledger = paper_readback if isinstance(paper_readback, dict) else {}
    signal = signal_source if isinstance(signal_source, dict) else {}
    market = market_source if isinstance(market_source, dict) else {}
    journal_present = ledger.get("paper_fill_count", 0) > 0 and ledger.get("reconciled") is True
    signal_verified = (signal.get("verified_github_provenance") or {}).get(
        "github_metadata_verified") is True
    market_verified = market.get("source_artifact_verified") is True
    cost_verified = ledger.get("paper_cost_arithmetic_reconciled") is True
    evidence_verified = bool(journal_present and signal_verified
                             and market_verified and cost_verified)
    return {
        "schema": "SKY_PAPER_ONLY_ACCEPTANCE_V1",
        "mode": "PAPER_ONLY",
        "broker_account_required_for_research": False,
        "broker_account_required_for_future_live_trading": True,
        "source_scan_run": status.get("run_url"),
        "source_scan_status": status.get("status") or "UNKNOWN",
        "scan_status_proves_tradable_signal": False,
        "precommitted_paper_signal_provided": signal_verified,
        "market_source_independently_verified": market_verified,
        "scan_id": status.get("scan_id"),
        "market_data_timestamp_valid": valid_time,
        "market_data_source": status.get("source"),
        "verified_quote_count": status.get("stage2_verified_executed_count"),
        "vwap_certified_count": status.get("candidate_chain_vwap_certified"),
        "live_ledger_verified": False,  # Not a PAPER_ONLY admission requirement
        "paper_ledger_provided": ledger.get("reconciled") is True,
        "paper_fills_provided": journal_present,
        "paper_after_cost_performance_verified": evidence_verified,
        "paper_performance_verdict": "VERIFIED_PAPER_ESTIMATE_RESEARCH_ONLY" if evidence_verified else "INSUFFICIENT_DATA",
        "expected_five_minute_slots": len(cadence_slots()),
        "scheduled_slot_evidence_provided": False,
        "schedule_reliability_verdict": "INSUFFICIENT_DATA",
        "live_trading_governance_verdict": "HOLD",
        "production_eligible": False,
        "live_order_enabled": False,
        "trade_action": "禁止交易",
        "note": "市場價格不代表真實或模擬成交；缺紙上交易逐筆事件、假設成交規則及成本，不得計算報酬率。排程必須核對真實 schedule event 與下游 artifact。",
    }


def main():
    status_file = Path("docs/SKY_CHAT_LATEST_STATUS.json")
    status = json.loads(status_file.read_text(encoding="utf-8")) if status_file.exists() else {}
    def read_report(path):
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, ValueError):
            return {}
    evidence_root = Path("output/sky_p0r_paper_ledger_readback")
    report = audit_status(
        status,
        paper_readback=read_report(evidence_root / "latest.json"),
        signal_source=read_report(evidence_root / "external_signal_source_status.json"),
        market_source=read_report(evidence_root / "market_source_status.json"),
    )
    out = Path("output/sky_paper_only_acceptance")
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (out / "latest.md").write_text(
        "# Sky PAPER_ONLY 研究驗收（無券商帳戶）\n\n"
        "🔴 正式實盤禁止交易；研究可用模擬帳本，但不可臆造成交。\n\n"
        f"- 真實掃描來源：{report['source_scan_run'] or '待確認'}\n"
        f"- 資料時間可解析：{report['market_data_timestamp_valid']}\n"
        f"- 待驗證模擬績效：{report['paper_performance_verdict']}\n"
        f"- 預期每五分鐘時段：{report['expected_five_minute_slots']}（09:00–13:30）\n"
        f"- 實際排程可靠性：{report['schedule_reliability_verdict']}\n"
        f"- 實盤治理：{report['live_trading_governance_verdict']}\n",
        encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
