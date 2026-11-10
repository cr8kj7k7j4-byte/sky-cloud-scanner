"""Read-only Sky v1.4 formal signal sufficiency audit.

Never infers A+ or a buy from a diagnostic sample, paid quote, or price
snapshot. Separates observable evidence from formal model readiness.
No paid data access, orders, network, or Production writes.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.cost_profiles import USER_CASH_DAYTRADE_20261022

SOURCE = Path("docs/SKY_CHAT_LATEST_STATUS.json")
OUTPUT = Path("output/sky_v14_readiness")


def evidence_check(status):
    """Return a deterministic, conservative gate audit from sanitized evidence."""
    if not isinstance(status, dict):
        raise ValueError("INVALID_STATUS_OBJECT")
    sample = status.get("v14_ticker_5m_samples")
    sample = sample if isinstance(sample, list) else []
    stage2 = status.get("stage2_quote_preview")
    stage2 = stage2 if isinstance(stage2, list) else []
    universe = status.get("universe_count")
    stage2_attempted = status.get("stage2_attempted_count")
    verified = status.get("stage2_verified_executed_count")
    fresh_market = status.get("fresh_executed_count")
    observed = status.get("observed_price_count")

    def nonnegative_int(v):
        return isinstance(v, int) and not isinstance(v, bool) and v >= 0

    def gate(name, passed, evidence, pending):
        return {"gate": name, "status": "EVIDENCED" if passed else "NOT_VERIFIED",
                "evidence": evidence, "pending": [] if passed else pending}

    findings = []
    checks = [
        ("universe_count", universe),
        ("observed_price_count", observed),
        ("fresh_executed_count", fresh_market),
        ("stage2_attempted_count", stage2_attempted),
        ("stage2_verified_executed_count", verified),
    ]
    if any(not nonnegative_int(n) for _, n in checks):
        findings.append("INVALID_OR_MISSING_COUNT_FIELD")
    elif observed > universe or verified > stage2_attempted or fresh_market > universe:
        findings.append("COUNT_CONTRADICTION")

    stage2_bounded = (
        nonnegative_int(stage2_attempted) and stage2_attempted > 0
        and verified == stage2_attempted
        and status.get("stage2_bounded_operational_probe_pass") is True
        and status.get("stage2_rate_limited_count") == 0
    )
    findings.append("BOUNDED_SAMPLE_ONLY_NOT_FULL_MARKET" if stage2_bounded else
                    "BOUNDED_SAMPLE_NOT_FULLY_VERIFIED")

    # Audit samples as observation only; avoid conflating Stage3 samples with
    # the full universe, certified VWAP or validated intraday strategy rules.
    candle_samples = [
        x for x in sample if isinstance(x, dict)
        and isinstance(x.get("valid_today_five_min_bars"), int)
        and x["valid_today_five_min_bars"] > 0
        and x.get("candles_timeframe") == "5"
    ]
    claimed_vwap = [x.get("avg_price_is_certified_vwap") is True
                    for x in sample if isinstance(x, dict)]
    certified_vwap = bool(sample) and all(claimed_vwap) and len(claimed_vwap) == len(sample)
    breakout_certified = bool(sample) and all(
        isinstance(x, dict) and x.get("breakout_quality_validated") is True
        for x in sample
    )
    full_rule_certified = bool(sample) and all(
        isinstance(x, dict) and x.get("v14_full_rule_validated") is True
        for x in sample
    )
    slip_certified = bool(sample) and all(
        isinstance(x, dict) and x.get("complete_execution_cost_rr") is True
        for x in sample
    )
    observed_quote_times = len([
        x for x in stage2 if isinstance(x, dict)
        and x.get("executed_trade_verified") is True
        and bool(x.get("last_trade_time"))
    ])
    formal_risk_confirmed = bool(stage2) and all(
        isinstance(x, dict)
        and (x.get("canonical_v14_p0c_audit") or {}).get("model_readiness", {})
           .get("p0_r_risk_inputs_complete") is True
        for x in stage2
    )
    formal_ledger_confirmed = bool(stage2) and all(
        isinstance(x, dict)
        and (x.get("canonical_v14_p0c_audit") or {}).get("model_readiness", {})
           .get("p0_k_evidence_eligible") is True
        for x in stage2
    )
    no_hard_block = (
        not findings or findings == ["BOUNDED_SAMPLE_ONLY_NOT_FULL_MARKET"]
    )
    # The public snapshot status is not a formal P0-C approved trade ledger.
    # Never promote even if it contains arbitrary booleans all set to true.
    gates = [
        gate("full_market_fresh_executions", False,
             {"universe": universe, "bulk_snapshot_fresh_trades": fresh_market,
              "stage2_attempted": stage2_attempted, "stage2_verified": verified},
             ["完整市場成交時間覆蓋及同時點資料品質未證實"]),
        gate("individual_quote_sample", stage2_bounded and no_hard_block,
             {"sample_verified": verified, "sample_attempted": stage2_attempted,
              "preview_verified_timestamps": observed_quote_times},
             ["受控樣本成交時間、429 或資料一致性尚未通過"]),
        gate("five_minute_candle_sample", bool(candle_samples) and no_hard_block,
             {"sample_count": len(sample), "samples_with_5m_candles": len(candle_samples)},
             ["需要來源時間語義、完成棒、連續性與全候選涵蓋"]),
        gate("official_vwap", False,
             {"sample_declared_vwap_certified": certified_vwap},
             ["未取得正式成交量加權均價（VWAP）來源與因果驗證"]),
        gate("breakout_and_anti_chase", False,
             {"sample_breakout_booleans": breakout_certified},
             ["未證明完整多週期突破品質、追高否決及反方檢查"]),
        gate("base_cash_cost_profile", True,
             {"profile_id": USER_CASH_DAYTRADE_20261022.profile_id,
              "buy_fee": USER_CASH_DAYTRADE_20261022.buy_commission_rate,
              "sell_fee": USER_CASH_DAYTRADE_20261022.sell_commission_rate,
              "sell_tax": USER_CASH_DAYTRADE_20261022.sell_tax_rate},
             []),
        gate("complete_slippage_fill_cost_rr", False,
             {"sample_complete_cost_rr_flags": slip_certified,
              "base_fee_profile_is_not_execution_cost": True},
             ["滑價、價差、實際成交機率、流動性衝擊及成本後 RR 未驗證"]),
        gate("p0_r_portfolio_ledger", False,
             {"sample_risk_readiness_flags": formal_risk_confirmed},
             ["當前持倉、成本、原停損、當日已實現損益及剩餘風險未經正式帳本核實"]),
        gate("p0_k_evidence_ledger", False,
             {"sample_p0_k_flags": formal_ledger_confirmed},
             ["正式 P0-K 時間戳、帳本與證據衝突檢查待核對"]),
        gate("full_v14_rule_validation", False,
             {"sample_full_rule_flags": full_rule_certified,
              "bridge_full_rule_validated": status.get("v14_full_rule_validation_complete")},
             ["僅樣本研究稽核，非全規則、成本後與前瞻策略驗證"]),
    ]
    conflict = (
        bool(findings and findings[0] in {"INVALID_OR_MISSING_COUNT_FIELD", "COUNT_CONTRADICTION"})
        or status.get("production_eligible") is not False
        or status.get("automatic_order") is not False
    )
    if conflict:
        findings.append("SOURCE_STATUS_CONFLICT_FAIL_CLOSED")
    return {
        "schema": "SKY_V14_FORMAL_READINESS_AUDIT_V1",
        "source_scan_id": status.get("scan_id"),
        "source_request_id": status.get("request_id"),
        "source_timestamp_tpe": status.get("data_timestamp"),
        "source_status": status.get("status"),
        "source": status.get("source"),
        "research_only": True,
        "production_eligible": False,
        "automatic_order": False,
        "a_plus_authorized": False,
        "now_action": "禁止交易",
        "verdict": "SOURCE_CONFLICT_BLOCKED" if conflict else "INSUFFICIENT_DATA",
        "checks": gates,
        "evidenced_count": sum(g["status"] == "EVIDENCED" for g in gates),
        "required_gate_count": len(gates),
        "findings": findings,
        "note": ("源資料為單次 GitHub 掃描的研究摘要，並非當前實際持倉帳本、"
                 "富果合約額度、完整市場成交覆蓋或正式策略績效。"
                 "基礎成本已校準，完整成交成本仍待驗證。")
    }


def markdown(report):
    lines = [
        "# Sky v1.4 當沖正式交易證據缺口（唯讀）",
        "",
        "資料時間：" + str(report["source_timestamp_tpe"]),
        "Run：" + str(report["source_scan_id"]),
        "**結論：🔴 禁止新進場、未驗證通過。**",
        "",
        "| 驗證項目 | 狀態 | 待確認 |", "| --- | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append("| " + check["gate"] + " | " + check["status"] +
                     " | " + "；".join(check["pending"]) + " |")
    lines += ["", "已建立研究資料與實測證據不等於具備正式進場資格。",
              "未經 W0／P0-G 正式審查，不得自動升版或下單。",
              ""]
    return "\n".join(lines)


def main():
    status = json.loads(SOURCE.read_text(encoding="utf-8"))
    report = evidence_check(status)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "latest.md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    if report["verdict"] == "SOURCE_CONFLICT_BLOCKED":
        raise SystemExit("SOURCE_CONFLICT_BLOCKED")


if __name__ == "__main__":
    main()
