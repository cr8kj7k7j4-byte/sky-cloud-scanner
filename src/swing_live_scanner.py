from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

from .decision_engine import first_gate
from .fugle import get_quote, get_ticker
from .official import fetch_mis_quotes, load_official_universe
from .ranking_engine import rank_screening_candidates

TZ = ZoneInfo("Asia/Taipei")
OUT = Path("output/swing_live")

MODE_META = {
    "swing": {
        "display_name": "Sky 波段快掃",
        "horizon": "3–20 個交易日",
        "strategy_status": "PRODUCTION_BASELINE_ACTIVE_RULE_SPEC_BLOCKED",
        "production_strategy": "Sky Swing V1.0",
        "candidate_label": "波段觀察候選",
        "note": "全市場即時資料可用；Sky Swing V1.0 exact executable rule spec 仍受 W0 governance blocker 約束，因此本掃描只產生可深查候選，不冒充完整 V1.0 買進訊號。",
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
    rows, warnings = fetch_mis_quotes(universe)

    twse_rows = [r for r in rows if r.get("exchange") == "TWSE"]
    tpex_rows = [r for r in rows if r.get("exchange") == "TPEx"]
    coverage_pct = round((len(rows) / len(universe) * 100.0), 2) if universe else 0.0

    operational_full_market_scan = bool(
        universe
        and universe_health.get("twse", 0) >= 500
        and universe_health.get("tpex", 0) >= 400
        and len(twse_rows) >= 400
        and len(tpex_rows) >= 300
        and coverage_pct >= 80.0
    )

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

    changes = sorted(_safe_float(r.get("change_pct")) for r in rows if r.get("change_pct") is not None)
    market_median = median(changes) if changes else 0.0

    candidates = [_build_candidate(r, market_median, mode) for r in eligible]
    candidates.sort(key=lambda x: (x["swing_live_score"], x.get("trade_value") or 0), reverse=True)
    candidates = candidates[: max(top_n, deep_n)]

    deep = []
    for item in candidates[:deep_n]:
        x = dict(item)
        try:
            ticker = get_ticker(x["symbol"])
            quote = get_quote(x["symbol"])
            x["fugle_close"] = quote.get("closePrice")
            x["fugle_high"] = quote.get("highPrice")
            x["fugle_low"] = quote.get("lowPrice")
            x["fugle_avg_price"] = quote.get("avgPrice")
            x["fugle_last_updated"] = quote.get("lastUpdated")
            x["limit_up_price"] = ticker.get("limitUpPrice")
            x["industry"] = ticker.get("industry")
            close = _safe_float(x.get("fugle_close"))
            limit_up = _safe_float(x.get("limit_up_price"))
            x["is_limit_up"] = bool(close > 0 and limit_up > 0 and close >= limit_up)
            x["data_status"] = "VERIFIED"
            if x["is_limit_up"]:
                x["candidate_action"] = "禁止交易"
                x["candidate_reason"] = "漲停／追高否決"
            else:
                x["candidate_action"] = "觀察"
                x["candidate_reason"] = MODE_META[mode]["note"]
        except PermissionError as exc:
            x["data_status"] = "PARTIAL_FUGLE_PERMISSION"
            x["candidate_action"] = "觀察"
            x["candidate_reason"] = str(exc)
        except Exception as exc:
            x["data_status"] = "PARTIAL_FUGLE_ERROR"
            x["candidate_action"] = "觀察"
            x["candidate_reason"] = f"{type(exc).__name__}: {exc}"
        deep.append(x)

    payload = {
        "generated_at": now.isoformat(),
        "mode": mode,
        "display_name": MODE_META[mode]["display_name"],
        "horizon": MODE_META[mode]["horizon"],
        "strategy_status": MODE_META[mode]["strategy_status"],
        "production_strategy": MODE_META[mode]["production_strategy"],
        "operational_full_market_scan": operational_full_market_scan,
        "strict_official_full_market_certified": False,
        "quote_coverage_pct": coverage_pct,
        "universe_count": len(universe),
        "quote_count": len(rows),
        "twse_quote_count": len(twse_rows),
        "tpex_quote_count": len(tpex_rows),
        "eligible_after_first_gate": len(eligible),
        "rejected_count": rejected,
        "market_median_change_pct": round(market_median, 4),
        "source_health": {
            "official_universe": universe_health,
            "intraday": {
                "source": "TWSE MIS TSE + OTC operational fallback",
                "note": "OTC is operational fallback and is not labelled TPEx-official real-time certification.",
            },
        },
        "warnings": warnings,
        "candidate_count": min(top_n, len(candidates)),
        "candidates": candidates[:top_n],
        "deep_candidates": deep,
        "governance_note": MODE_META[mode]["note"],
    }

    suffix = "swing5d" if mode == "swing5d" else "swing"
    (OUT / f"latest_{suffix}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        f"{MODE_META[mode]['display_name']}｜{now:%Y-%m-%d %H:%M}",
        f"全市場實務掃描：{'是' if operational_full_market_scan else '否'}｜覆蓋率 {coverage_pct}%｜母池 {len(universe)}｜報價 {len(rows)}",
        f"TWSE {len(twse_rows)}｜TPEx/OTC {len(tpex_rows)}｜初篩通過 {len(eligible)}",
        f"策略狀態：{MODE_META[mode]['strategy_status']}",
        "",
        "【候選】",
    ]
    if not deep:
        lines.append("目前沒有符合條件的新進場標的。")
    else:
        for i, x in enumerate(deep, 1):
            lines.append(
                f"{i}. {x.get('symbol')} {x.get('name','')}｜"
                f"現價 {x.get('fugle_close', x.get('last'))}｜"
                f"漲跌 {round(_safe_float(x.get('change_pct')),2)}%｜"
                f"相對市場 {x.get('relative_to_market_pct')}%｜"
                f"{x.get('candidate_action')}｜{x.get('data_status')}"
            )
    lines += ["", "【治理】", MODE_META[mode]["note"]]
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
