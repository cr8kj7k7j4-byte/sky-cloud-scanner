"""Fail-closed read-only evidence chain: Snapshot -> Quote -> 5m -> VWAP -> P0-R.

Does not perform provider calls; joins existing Stage1/Stage2/Stage3 observations.
No structural replacement of formal 80% whole-market quote gate, no A+, no orders.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.cost_profiles import USER_CASH_DAYTRADE_20261022
from src.risk_engine import evaluate_trade
from research.sky_stage5_vwap_cost_evidence import review_quote_vwap_evidence, review_cost_evidence

SCHEMA = "SKY_CANDIDATE_E2E_EVIDENCE_CHAIN_V1"


def _time(value):
    if not isinstance(value, str):
        return None
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return t if t.utcoffset() is not None else None
    except ValueError:
        return None


def build(stage1, stage2, stage3):
    """Join only existing verified records, never fabricate missing bar or risk evidence."""
    if stage1.get("schema") != "SKY_STAGE1_FUGLE_SNAPSHOT_CANDIDATES_V1":
        raise ValueError("INVALID_STAGE1_SCHEMA")
    if stage2.get("schema") != "SKY_STAGE2_BOUNDED_QUOTE_EVIDENCE_V1":
        raise ValueError("INVALID_STAGE2_SCHEMA")
    if stage3.get("schema") != "SKY_V14_TICKER_5M_RESEARCH_PROVENANCE_V1":
        raise ValueError("INVALID_STAGE3_SCHEMA")
    if stage2.get("production_eligible") is not False or stage3.get("production_eligible") is not False:
        raise ValueError("RESEARCH_STATUS_CONFLICT")
    candidates = stage1.get("candidates")
    rows = stage2.get("results")
    bars = stage3.get("samples")
    if not all(isinstance(v, list) for v in (candidates, rows, bars)):
        raise ValueError("INVALID_STAGE_ROWS")

    candidate_by_key = {}
    for item in candidates:
        if not isinstance(item, dict):
            raise ValueError("INVALID_CANDIDATE")
        key = (item.get("exchange"), str(item.get("symbol")))
        if key in candidate_by_key or key[0] not in ("TWSE", "TPEx"):
            raise ValueError("DUPLICATE_OR_INVALID_CANDIDATE")
        candidate_by_key[key] = item
    stage3_by_key = {}
    for item in bars:
        if not isinstance(item, dict):
            raise ValueError("INVALID_5M_ROW")
        key = (item.get("exchange"), str(item.get("symbol")))
        if key in stage3_by_key:
            raise ValueError("DUPLICATE_5M_ROW")
        stage3_by_key[key] = item

    stage2_seen = set()
    chain = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("INVALID_QUOTE_ROW")
        key = (row.get("exchange"), str(row.get("symbol")))
        if key in stage2_seen or key not in candidate_by_key:
            raise ValueError("QUOTE_NOT_IN_SNAPSHOT_CANDIDATES_OR_DUPLICATE")
        stage2_seen.add(key)
        stage1_row = candidate_by_key[key]
        candle = stage3_by_key.get(key)
        quote_time = _time(row.get("last_trade_time"))
        verified_quote = (
            row.get("executed_trade_verified") is True
            and row.get("status") == "FRESH_EXECUTED_TRADE"
            and quote_time is not None
            and quote_time.date() == _time(stage2.get("checked_at_tpe")).date()
            if _time(stage2.get("checked_at_tpe")) is not None else False
        )
        # Retain the original quote verifier as authority; stage report merely
        # checks its status and timestamp are mutually consistent.
        micro = row.get("microstructure") if isinstance(row.get("microstructure"), dict) else {}
        five_min_observed = (
            verified_quote and isinstance(candle, dict)
            and candle.get("candles_timeframe") == "5"
            and isinstance(candle.get("valid_today_five_min_bars"), int)
            and not isinstance(candle.get("valid_today_five_min_bars"), bool)
            and candle["valid_today_five_min_bars"] >= 1
        )
        causal_verified = (
            five_min_observed and candle.get("bar_timestamp_semantics_certified") is True
            and candle.get("bar_sequence_valid") is True
            and candle.get("status") == "CANDLE_TICKER_RESEARCH_READY_NOT_TRADE"
        )
        # avgPrice can be shown as a provider average-price observation, NEVER as certified VWAP.
        avg_price = micro.get("average_price") if verified_quote else None
        vwap_source_audit = review_quote_vwap_evidence(micro if verified_quote else {})
        cost_source_audit = review_cost_evidence()
        vwap_certified = bool(causal_verified and candle.get("avg_price_is_certified_vwap") is True)
        # Formal P0-R cannot be checked from synthetic zero holdings. Call only
        # with absent price levels, forcing the canonical risk engine to block.
        risk = evaluate_trade(
            entry=row.get("verified_trade_price") if verified_quote else None,
            stop=None, target=None, account_equity=0,
        )
        if risk.get("status") != "RISK_INPUT_REQUIRED" or risk.get("portfolio_allowed") is not False:
            raise ValueError("RISK_FAIL_CLOSED_CONTRACT_BROKEN")

        missing = []
        # Stage1 snapshot price is NOT an entry price. Reject a quote that crosses
        # the original user price ceiling after the Stage1 observation.
        verified_price = row.get("verified_trade_price") if verified_quote else None
        latest_price_within_limit = (
            verified_quote and isinstance(verified_price, (float, int))
            and not isinstance(verified_price, bool)
            and 0 < verified_price < 100
        )
        if verified_quote and not latest_price_within_limit:
            missing.append("VERIFIED_TRADE_PRICE_NOT_BELOW_100")
        if not verified_quote:
            missing.append("FRESH_EXECUTED_TRADE")
        if not five_min_observed:
            missing.append("FIVE_MINUTE_BAR_SAMPLE")
        if not causal_verified:
            missing.append("FIVE_MINUTE_BAR_CAUSAL_CERTIFICATION")
        if not vwap_certified:
            missing.append("OFFICIAL_VWAP_PROVENANCE")
        missing += ["BREAKOUT_ANTI_CHASE_FULL_RULE", "EXECUTION_SLIPPAGE_FILL_COST_RR",
                    "P0_R_CURRENT_PORTFOLIO_LEDGER", "P0_K_EVIDENCE_LEDGER",
                    "W0_P0_G_FORMAL_PROMOTION"]
        chain.append({
            "symbol": key[1], "exchange": key[0],
            "snapshot_observed_price": stage1_row.get("observed_price"),
            "snapshot_is_execution_verified": False,
            "quote_verified": verified_quote,
            "verified_trade_price_below_100": latest_price_within_limit,
            "verified_trade_price": row.get("verified_trade_price") if verified_quote else None,
            "last_trade_time": row.get("last_trade_time") if verified_quote else None,
            "quote_status": row.get("status"),
            "quality_reasons": micro.get("quality_reasons") or [],
            "five_minute_observed": five_min_observed,
            "five_minute_causal_certified": causal_verified,
            "five_minute_sample_bars": candle.get("valid_today_five_min_bars") if five_min_observed else None,
            "ticker_status": candle.get("status") if candle else "NOT_QUERIED_BOUNDED_SAMPLE",
            "provider_avg_price_observation": avg_price,
            "vwap_certified": vwap_certified,
            "vwap_source": "NOT_CERTIFIED" if not vwap_certified else "CANDIDATE_CLAIM_REQUIRES_W0_REVIEW",
            "vwap_source_consistency_audit": vwap_source_audit,
            "execution_cost_provenance_audit": cost_source_audit,
            "cost_profile": USER_CASH_DAYTRADE_20261022.profile_id,
            "base_round_trip_cost_pct": round(
                100 * (USER_CASH_DAYTRADE_20261022.buy_commission_rate
                       + USER_CASH_DAYTRADE_20261022.sell_commission_rate
                       + USER_CASH_DAYTRADE_20261022.sell_tax_rate), 4),
            "complete_execution_cost_rr": False,
            "p0_r_status": risk["status"],
            "risk_required_inputs": risk["required_inputs"],
            "risk_recommended_shares": 0,
            "evidence_missing": missing,
            "classification": "X", "action": "禁止交易",
            "a_plus": False, "production_eligible": False, "automatic_order": False,
        })

    for key in stage3_by_key:
        if key not in stage2_seen:
            raise ValueError("STAGE3_NOT_IN_STAGE2")
    return {
        "schema": SCHEMA,
        "scope": "BOUNDED_STAGE2_CANDIDATES_ONLY_NOT_FULL_MARKET",
        "stage1_candidate_count": stage1.get("candidate_count"),
        "stage2_attempted_count": stage2.get("attempted_count"),
        "stage2_quote_verified_count": sum(r["quote_verified"] for r in chain),
        "stage3_five_minute_observed_count": sum(r["five_minute_observed"] for r in chain),
        "stage3_causally_certified_count": sum(r["five_minute_causal_certified"] for r in chain),
        "vwap_certified_count": sum(r["vwap_certified"] for r in chain),
        "formal_market_coverage_certified": False,
        "risk_ledger_verified": False,
        "full_strategy_validated": False,
        "production_eligible": False, "automatic_order": False,
        "trade_decision": "🔴 禁止新進場、未驗證通過",
        "rows": chain,
        "note": "既有三階段資料鏈已接通；研究樣本不是全市場成交驗證、可執行價格或 A+。",
    }


def markdown(report):
    lines = [
        "# Sky 候選股 Snapshot → Quote → 5m/VWAP → P0-R 證據鏈",
        "",
        "**🔴 禁止新進場、未驗證通過**",
        "Stage1 候選：" + str(report["stage1_candidate_count"]),
        "Stage2 成交時間核實：" + str(report["stage2_quote_verified_count"]) + "/" + str(report["stage2_attempted_count"]),
        "Stage3 已觀察 5 分鐘棒：" + str(report["stage3_five_minute_observed_count"]),
        "正式 VWAP 認證：" + str(report["vwap_certified_count"]),
        "",
        "| 股票 | Snapshot 價 | 成交價／時間 | 5m | VWAP | P0-R | 動作 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for x in report["rows"]:
        last = (str(x["verified_trade_price"]) + " / " + str(x["last_trade_time"])
                if x["quote_verified"] else "待確認")
        lines.append("| " + x["symbol"] + " | " + str(x["snapshot_observed_price"]) +
                     "（觀察） | " + last +
                     " | " + ("樣本已觀察，因果未認證" if x["five_minute_observed"] else "待確認") +
                     " | " + ("已認證" if x["vwap_certified"] else "待確認") +
                     " | " + x["p0_r_status"] + " | 禁止交易 |")
    lines += ["", "現股當沖基本成本已校準，滑價、成交率、流動性衝擊與完整成本後 RR 待驗證。",
              "必須經 W0/P0-G 審查才可變更正式市場 Gate。", ""]
    return "\n".join(lines)


def write(stage1, stage2, stage3, path):
    report = build(stage1, stage2, stage3)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    target.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    return report
