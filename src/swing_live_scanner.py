from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

from .decision_engine import first_gate
from .fugle import get_quote, get_ticker
from .official import fetch_fugle_snapshot_quotes, fetch_mis_quotes, load_official_universe
from .ranking_engine import rank_screening_candidates
from .sky_mobile_table import render_mobile_table
from .realtime_quote_evidence import fugle_executed_trade, validate_whole_market_rows
from .swing5d_information_table import COLUMNS, build_swing5d_13col_rows, render_swing5d_13col_table

TZ = ZoneInfo("Asia/Taipei")
OUT = Path("output/swing_live")

MODE_META = {
    "swing": {
        "display_name": "Sky 波段快掃",
        "horizon": "3–20 個交易日",
        "strategy_status": "PRODUCTION_BASELINE_ACTIVE_RULE_SPEC_BLOCKED",
        "production_strategy": "Sky Swing V1.0",
        "candidate_label": "波段觀察候選",
        "note": "Sky Swing V1.0 exact executable rule spec 仍受 W0 governance blocker 約束，因此本掃描只產生可深查候選，不冒充完整 V1.0 買進訊號。",
    },
    "swing5d": {
        "display_name": "Sky Swing 5D 快掃",
        "horizon": "5 個交易日研究視窗",
        "strategy_status": "RESEARCH_ONLY_HOLD",
        "production_strategy": None,
        "candidate_label": "5D 研究候選",
        "note": "Swing 5D 為研究候選/HOLD；即時資料接通不代表策略已通過完整穩定性與 Promotion Gates。",
    },
}


def coverage_governance_notice(operational_full_market_scan, coverage_pct):
    """Only certify operational quote coverage after the existing market gate."""
    if operational_full_market_scan:
        return "全市場實務報價覆蓋驗證通過；OTC MIS 仍僅為操作備援，非 TPEx 官方完整即時行情。"
    return (
        f"全市場即時行情資料未通過驗證（有效報價覆蓋率 {coverage_pct}%）；"
        "候選僅供觀察，不可據此產生 A+ 或可執行買進價。"
        "OTC MIS 僅為操作備援，非 TPEx 官方完整即時行情。"
    )


def _safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def _swing_priority(row):
    """Operational candidate ordering only; not probability or validated alpha."""
    cp = _safe_float(row.get("change_pct"))
    trade_value = max(0.0, _safe_float(row.get("trade_value")))
    last = _safe_float(row.get("last"))
    high = _safe_float(row.get("high"))
    low = _safe_float(row.get("low"))
    open_ = _safe_float(row.get("open"))
    range_pct = ((high - low) / last * 100.0) if last > 0 and high >= low > 0 else 99.0
    close_location = ((last - low) / (high - low)) if high > low and last > 0 else 0.5
    above_open = 1.0 if last > open_ > 0 else 0.0

    # Transparent operational pre-ranking. This does NOT replace a governed Swing rule.
    return (
        cp * 1.5
        + min(2.0, trade_value / 100_000_000.0)
        + close_location * 2.0
        + above_open
        - max(0.0, range_pct - 8.0) * 0.25
    )


def _build_candidate(row, universe_change_median, mode):
    item = dict(row)
    item["swing_live_score"] = round(_swing_priority(item), 4)
    item["relative_to_market_pct"] = round(
        _safe_float(item.get("change_pct")) - universe_change_median, 4
    )
    item["candidate_type"] = MODE_META[mode]["candidate_label"]
    item["candidate_scope"] = "WHOLE_MARKET_OPERATIONAL_SCREEN"
    item["strategy_signal"] = False
    item["production_eligible"] = False if mode == "swing5d" else None
    return item


def run(mode="swing5d", top_n=20, deep_n=8):
    if mode not in MODE_META:
        raise ValueError(f"unsupported mode: {mode}")

    now = datetime.now(TZ)
    OUT.mkdir(parents=True, exist_ok=True)

    universe, universe_health = load_official_universe()
    rows, warnings = fetch_fugle_snapshot_quotes(universe, trading_date=now.date().isoformat())
    snapshot_count = len(rows)
    if not universe or (len(rows) / len(universe)) < 0.80:
        fallback_rows, fallback_warnings = fetch_mis_quotes(universe)
        merged = {r["symbol"]: r for r in fallback_rows}
        # Prefer the validated bulk snapshot on duplicate symbols.
        merged.update({r["symbol"]: r for r in rows})
        rows = list(merged.values())
        warnings.extend(fallback_warnings)
    # The bulk snapshot may carry useful observed price fields without
    # independent last-execution timestamps. Preserve it as an UNVERIFIED
    # observation tier, never as executable quotes or whole-market signals.
    raw_observations = list(rows)
    quote_audit = validate_whole_market_rows(
        universe, rows, now=datetime.now(TZ),
        min_coverage_pct=80.0, min_exchange_pct=70.0,
    )
    rows = quote_audit["accepted_rows"]
    valid_symbols = {str(row.get("symbol")) for row in rows}
    unverified_snapshot = []
    for raw in raw_observations:
        if raw.get("quote_source") != "Fugle bulk snapshot":
            continue
        sym = str(raw.get("symbol") or "")
        price = _safe_float(raw.get("last"))
        volume = _safe_float(raw.get("volume"))
        if sym in valid_symbols or not sym or not 0 < price < 100 or volume <= 0:
            continue
        unverified_snapshot.append({
            "symbol": sym,
            "name": raw.get("name"),
            "exchange": raw.get("exchange"),
            "indicative_last_price": price,
            "trade_volume": volume,
            "trade_value": raw.get("trade_value"),
            "snapshot_date": raw.get("quote_date"),
            "snapshot_updated_at": raw.get("quote_time"),
            "last_trade_timestamp": raw.get("last_trade_timestamp"),
            "source": "Fugle bulk snapshot",
            "data_status": "UNVERIFIED_EXECUTED_TRADE_TIME",
            "candidate_scope": "BULK_SNAPSHOT_INDICATIVE_ONLY",
            "candidate_action": "觀察",
            "strategy_signal": False,
            "production_eligible": False,
            "buy_trigger": None,
            "stop": None,
            "target": None,
            "research_score": None,
        })
    unverified_snapshot.sort(key=lambda x: _safe_float(x.get("trade_value")), reverse=True)
    all_snapshot_observations = list(unverified_snapshot)
    unverified_snapshot = unverified_snapshot[:20]
    snapshot_exchange_counts = {
        ex: sum(row.get("exchange") == ex for row in raw_observations
                if row.get("quote_source") == "Fugle bulk snapshot")
        for ex in ("TWSE", "TPEx")
    }
    snapshot_coverage_pct = round(
        100.0 * len({str(row.get("symbol")) for row in raw_observations
                     if row.get("quote_source") == "Fugle bulk snapshot"}) / len(universe), 2
    ) if universe else 0.0
    if not quote_audit["valid_whole_market_operational"]:
        warnings.append(
            "BLOCKED_EXTERNAL_DATA: full-market fresh executed-trade coverage "
            "failed; withhold all broad-market ranked candidate signals."
        )
    source_breakdown = {
        "fugle_bulk_snapshot": snapshot_count,
        "mis_fallback": sum(r.get("quote_source") == "TWSE MIS" for r in rows),
    }

    twse_rows = [r for r in rows if r.get("exchange") == "TWSE"]
    tpex_rows = [r for r in rows if r.get("exchange") == "TPEx"]
    coverage_pct = round((len(rows) / len(universe) * 100.0), 2) if universe else 0.0

    operational_full_market_scan = bool(
        quote_audit["valid_whole_market_operational"]
        and universe
        and universe_health.get("twse", 0) >= 500
        and universe_health.get("tpex", 0) >= 400
        and len(twse_rows) >= 400
        and len(tpex_rows) >= 300
        and coverage_pct >= 80.0
    )

    coverage_notice = coverage_governance_notice(operational_full_market_scan, coverage_pct)

    eligible = []
    rejected = 0
    for row in rows:
        ok, reasons = first_gate(row)
        if not ok:
            rejected += 1
            continue
        cp = _safe_float(row.get("change_pct"))
        # Swing live anti-chase prefilter only. Hard limit-up confirmation is done in deep dive.
        if cp >= 9.0:
            rejected += 1
            continue
        eligible.append(row)

    # Keep observed, individually verified rows visible even when the whole-market
    # gate fails. They are PARTIAL_SAMPLE_OBSERVATIONS, never full-market signals.
    # Do not infer market-relative strength from an incomplete sample.
    observed_sample_only = not operational_full_market_scan
    changes = sorted(_safe_float(r.get("change_pct")) for r in rows if r.get("change_pct") is not None)
    market_median = median(changes) if changes else 0.0

    candidates = [_build_candidate(r, market_median, mode) for r in eligible]
    for candidate in candidates:
        if observed_sample_only:
            candidate["candidate_scope"] = "PARTIAL_SAMPLE_OBSERVATION"
            candidate["relative_to_market_pct"] = None
            candidate["market_relative_verified"] = False
            candidate["strategy_signal"] = False
            candidate["production_eligible"] = False
            candidate["candidate_action"] = "觀察"
            candidate["candidate_reason"] = "全市場資料未通過驗證；僅為有效成交資料中的局部觀察，禁止新進場。"
        else:
            candidate["market_relative_verified"] = True
    candidates.sort(key=lambda x: (x["swing_live_score"], x.get("trade_value") or 0), reverse=True)
    candidates = candidates[: max(top_n, deep_n)]

    deep = []
    for item in candidates[:deep_n]:
        x = dict(item)
        try:
            ticker = get_ticker(x["symbol"])
            quote = get_quote(x["symbol"])
            verified_last, trade_time, evidence_status = fugle_executed_trade(
                quote, now, max_age_seconds=180
            )
            if evidence_status != "FRESH_EXECUTED_TRADE":
                x["fugle_close"] = None
                x["fugle_last_updated"] = (
                    trade_time.isoformat() if trade_time else None
                )
                x["data_status"] = "UNVERIFIED_EXECUTED_TRADE"
                x["candidate_action"] = "等待"
                x["candidate_reason"] = (
                    "無可驗證的當日最新成交價／成交時間：" + evidence_status
                )
                deep.append(x)
                continue
            x["fugle_close"] = verified_last
            x["fugle_high"] = quote.get("highPrice")
            x["fugle_low"] = quote.get("lowPrice")
            x["fugle_avg_price"] = quote.get("avgPrice")
            x["fugle_last_updated"] = trade_time.isoformat()
            x["limit_up_price"] = ticker.get("limitUpPrice")
            x["industry"] = ticker.get("industry")
            close = _safe_float(x.get("fugle_close"))
            limit_up = _safe_float(x.get("limit_up_price"))
            x["is_limit_up"] = bool(close > 0 and limit_up > 0 and close >= limit_up)
            x["data_status"] = "VERIFIED_EXECUTED_TRADE"
            if x["is_limit_up"]:
                x["candidate_action"] = "禁止交易"
                x["candidate_reason"] = "漲停／追高否決"
            else:
                x["candidate_action"] = "觀察"
                x["candidate_reason"] = coverage_notice + " " + MODE_META[mode]["note"]
        except PermissionError as exc:
            x["data_status"] = "PARTIAL_FUGLE_PERMISSION"
            x["candidate_action"] = "觀察"
            x["candidate_reason"] = str(exc)
        except Exception as exc:
            x["data_status"] = "PARTIAL_FUGLE_ERROR"
            x["candidate_action"] = "觀察"
            x["candidate_reason"] = f"{type(exc).__name__}: {exc}"
        deep.append(x)

    # A bulk snapshot has no lastTrade.time. Deep-confirm a bounded shortlist
    # through the per-symbol execution endpoint without upgrading the market gate.
    snapshot_deep_confirmation = []
    if mode == "swing5d" and not operational_full_market_scan:
        for item in unverified_snapshot[:deep_n]:
            confirmation = {
                "symbol": item["symbol"],
                "name": item.get("name"),
                "exchange": item.get("exchange"),
                "snapshot_indicative_price": item.get("indicative_last_price"),
                "source": "Fugle intraday quote / individual execution check",
                "strategy_signal": False,
                "production_eligible": False,
                "candidate_scope": "INDIVIDUAL_EXECUTION_CHECK_ONLY",
                "candidate_action": "觀察",
                "verified_executed_price": None,
                "verified_executed_at": None,
                "data_status": "NOT_VERIFIED",
            }
            try:
                quote = get_quote(item["symbol"])
                verified_price, verified_at, evidence_status = fugle_executed_trade(
                    quote, datetime.now(TZ), max_age_seconds=180
                )
                confirmation["data_status"] = evidence_status
                if evidence_status == "FRESH_EXECUTED_TRADE":
                    confirmation["verified_executed_price"] = verified_price
                    confirmation["verified_executed_at"] = verified_at.isoformat()
                    if verified_price >= 100:
                        confirmation["candidate_action"] = "禁止交易"
                        confirmation["reason"] = "超出新進場股價限制"
            except Exception as exc:
                confirmation["data_status"] = "FUGLE_INDIVIDUAL_QUOTE_ERROR"
                confirmation["reason"] = f"{type(exc).__name__}: {str(exc)[:120]}"
            snapshot_deep_confirmation.append(confirmation)

    payload = {
        "generated_at": now.isoformat(),
        "mode": mode,
        "display_name": MODE_META[mode]["display_name"],
        "horizon": MODE_META[mode]["horizon"],
        "strategy_status": MODE_META[mode]["strategy_status"],
        "production_strategy": MODE_META[mode]["production_strategy"],
        "operational_full_market_scan": operational_full_market_scan,
        "observation_mode": "PARTIAL_SAMPLE_ONLY" if observed_sample_only else "WHOLE_MARKET_OBSERVATION",
        "trade_decision": "禁止新進場：研究策略未通過正式驗證",
        "observations_are_trade_signals": False,
        "observed_sample_count": len(rows),
        "unverified_snapshot_observation_count": len(all_snapshot_observations),
        "snapshot_coverage_pct": snapshot_coverage_pct,
        "snapshot_exchange_counts": snapshot_exchange_counts,
        "snapshot_observations_full_artifact": f"output/swing_live/snapshot_observations_{mode}.json",
        "snapshot_individual_confirmation": snapshot_deep_confirmation,
        "snapshot_individual_verified_count": sum(
            row.get("data_status") == "FRESH_EXECUTED_TRADE"
            for row in snapshot_deep_confirmation
        ),
        "unverified_snapshot_observations": unverified_snapshot,
        "snapshot_observation_warning": (
            "批量報價已取得，但缺乏可驗證的最近成交時間；"
            "indicative_last_price僅為來源觀察值，非已認證即時成交價，不可作為交易觸發。"
        ),
        "strict_official_full_market_certified": False,
        "live_whole_market_certified": operational_full_market_scan,
        "quote_scope": quote_audit["quote_scope"],
        "live_market_evidence": {
            k: v for k, v in quote_audit.items() if k != "accepted_rows"
        },
        "market_data_gate": (
            "PASS_OPERATIONAL_WHOLE_MARKET_LIVE_RESEARCH_ONLY"
            if operational_full_market_scan else "BLOCKED_EXTERNAL_DATA_NO_TRADE"
        ),
        "quote_coverage_pct": coverage_pct,
        "universe_count": len(universe),
        "quote_count": len(rows),
        "quote_source_breakdown": source_breakdown,
        "twse_quote_count": len(twse_rows),
        "tpex_quote_count": len(tpex_rows),
        "eligible_after_first_gate": len(eligible),
        "rejected_count": rejected,
        "market_median_change_pct": round(market_median, 4),
        "source_health": {
            "official_universe": universe_health,
            "intraday": {
                "source": "Fugle TSE/OTC bulk snapshot, TWSE MIS fallback",
                "note": "OTC is operational fallback and is not labelled TPEx-official real-time certification.",
            },
        },
        "warnings": warnings,
        "candidate_count": min(top_n, len(candidates)),
        "candidates": candidates[:top_n],
        "deep_candidates": deep,
        "governance_note": coverage_notice + " " + MODE_META[mode]["note"],
    }

    suffix = "swing5d" if mode == "swing5d" else "swing"
    if mode == "swing5d":
        information_rows_13col = build_swing5d_13col_rows(
            all_snapshot_observations, snapshot_deep_confirmation
        )
        payload["information_columns_13col"] = list(COLUMNS)
        payload["information_preview_13col"] = information_rows_13col[:20]
        payload["information_count_13col"] = len(information_rows_13col)
        full_observations = {
            "generated_at": now.isoformat(),
            "information_columns_13col": list(COLUMNS),
            "information_rows_13col": information_rows_13col,
            "source": "Fugle bulk snapshot",
            "observation_scope": "BULK_SNAPSHOT_INDICATIVE_ONLY",
            "snapshot_coverage_pct": snapshot_coverage_pct,
            "snapshot_exchange_counts": snapshot_exchange_counts,
            "observed_symbols": len(all_snapshot_observations),
            "trade_eligibility": "禁止新進場：未驗證逐股成交時間及策略資格",
            "sorting": "trade_value_desc_NOT_validated_swing_5D_alpha",
            "data": all_snapshot_observations,
        }
        (OUT / f"snapshot_observations_{mode}.json").write_text(
            json.dumps(full_observations, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    (OUT / f"latest_{suffix}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        f"{MODE_META[mode]['display_name']}｜{now:%Y-%m-%d %H:%M}",
        f"全市場實務掃描：{'是' if operational_full_market_scan else '否'}｜覆蓋率 {coverage_pct}%｜母池 {len(universe)}｜報價 {len(rows)}",
        f"TWSE {len(twse_rows)}｜TPEx/OTC {len(tpex_rows)}｜初篩通過 {len(eligible)}",
        f"策略狀態：{MODE_META[mode]['strategy_status']}",
        "🔴 禁止新進場、未驗證通過；下列資料僅供自主研究判斷，不是可執行交易訊號。",
        f"觀察模式：{'部分已驗證樣本' if observed_sample_only else '全市場觀察'}｜可供排序樣本 {len(eligible)}",
        f"未驗證成交時間的富果批量觀察：{len(unverified_snapshot)} 檔（最多顯示20檔，非全市場排名）",
        "批量參考價不是認證即時成交價；不產生買進觸發、停損或停利。",
        "",
        render_mobile_table(deep),
        "",
        "【13欄｜富果已取得資訊觀察，不代表5D交易訊號】",
        render_swing5d_13col_table(payload.get("information_preview_13col", [])) if mode == "swing5d" else "",
        "即時價只顯示逐股成交時間複核通過者；批量參考價與資料時間保留於JSON，不冒充即時成交。",
        "",
        "【治理】",
        coverage_notice,
        MODE_META[mode]["note"],
        "多方／空方評分為證據評分，不是勝率或機率；無治理後買點/停損時以 — 顯示。",
    ]
    text = "\n".join(lines)
    (OUT / f"latest_{suffix}.txt").write_text(text, encoding="utf-8")
    print(text)
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["swing", "swing5d"], default="swing5d")
    ap.add_argument("--top-n", type=int, default=20)
    ap.add_argument("--deep-n", type=int, default=8)
    args = ap.parse_args()
    run(args.mode, args.top_n, args.deep_n)


if __name__ == "__main__":
    main()
