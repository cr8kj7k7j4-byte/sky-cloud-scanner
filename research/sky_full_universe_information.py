"""Read-only all-universe market observation; NEVER grants production trading permission.

Every official symbol remains in the output, even when its quote is missing.
A quote without a confirmed fresh execution can be observed, clearly labelled,
but cannot count toward verified live coverage or become a trade signal.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.fugle import snapshot_quotes
from src.official import load_official_universe
from src.realtime_quote_evidence import timestamp_tpe

TZ = ZoneInfo("Asia/Taipei")
OUTPUT_DIR = Path("output/sky_quickscan_information")
MARKET = {"TWSE": "TSE", "TPEx": "OTC"}
# Fugle explicitly separates Taiwan Innovation Board (TIB) from TSE.
# TWSE STOCK_DAY_ALL still includes 创-board securities in the TWSE universe.
INNOVATION_BOARD = "TIB"


def expected_snapshot_market(meta):
    """Official TWSE suffix is discovery evidence, NOT an execution permit."""
    if meta.get("exchange") == "TWSE" and (
        meta.get("market") == INNOVATION_BOARD
        or str(meta.get("name") or "").endswith("創")
    ):
        return INNOVATION_BOARD
    return MARKET[meta["exchange"]]



def numeric(value):
    try:
        result = float(value)
        if result != result or result in (float("inf"), float("-inf")):
            return None
        return result
    except (ValueError, TypeError, OverflowError):
        return None


def record(meta, payload, source_date, checked_at):
    """No price fabrication, no unverified executions promoted to fresh."""
    result = {
        "symbol": str(meta["symbol"]), "name": meta.get("name", ""),
        "exchange": meta["exchange"], "market": expected_snapshot_market(meta),
        "source": "Fugle paid bulk snapshot" if payload is not None else "NO_SNAPSHOT_ROW",
        "data_status": "MISSING_QUOTE", "last_price": None,
        "change_pct": None, "volume": None, "last_trade_time": None,
        "time_age_seconds": None, "snapshot_observed_at": None,
        "snapshot_source_date": source_date or None, "snapshot_is_trial": False,
        "research_only": True,
        "production_eligible": False, "trade_signal": False,
    }
    if not isinstance(payload, dict):
        return result
    # Collection time is informational only, not an executed-trade timestamp.
    result["snapshot_observed_at"] = checked_at.isoformat()
    result["snapshot_is_trial"] = payload.get("isTrial") is True
    trade = payload.get("lastTrade")
    trade = trade if isinstance(trade, dict) else {}
    price = numeric(trade.get("price"))
    if price is None:
        price = numeric(payload.get("lastPrice"))
    if price is not None and price <= 0:
        price = None
    result["last_price"] = price
    result["volume"] = numeric(payload.get("tradeVolume"))
    result["open_price"] = numeric(payload.get("openPrice"))
    result["high_price"] = numeric(payload.get("highPrice"))
    result["low_price"] = numeric(payload.get("lowPrice"))
    prev = numeric(payload.get("previousClose"))
    change = numeric(payload.get("changePercent"))
    if change is None and price is not None and prev is not None and prev > 0:
        change = (price / prev - 1) * 100
    result["change_pct"] = round(change, 3) if change is not None else None

    # Never use snapshot refresh time as executed-trade time.
    ts = timestamp_tpe(trade.get("time"))
    if ts is not None:
        result["last_trade_time"] = ts.isoformat()
        result["time_age_seconds"] = round((checked_at - ts).total_seconds(), 1)
    if source_date != checked_at.date().isoformat():
        result["data_status"] = "SNAPSHOT_DATE_NOT_TODAY"
    elif price is None:
        result["data_status"] = "MISSING_EXECUTED_PRICE"
    elif ts is None:
        result["data_status"] = "UNVERIFIED_EXECUTION_TIME"
    elif ts.date() != checked_at.date() or result["time_age_seconds"] > 180:
        result["data_status"] = "STALE_EXECUTION_TIME"
    elif result["time_age_seconds"] < -30:
        result["data_status"] = "FUTURE_EXECUTION_TIME"
    elif payload.get("isTrial") is True:
        result["data_status"] = "TRIAL_QUOTE"
    else:
        result["data_status"] = "FRESH_EXECUTED_TRADE"
    return result


# Information transparency is separate from trade permission. Required fields
# are serialized even if no verified value exists.
REQUIRED_INFORMATION_COLUMNS = (
    "股票代碼", "股票名稱", "即時價", "最近觀察價（可能延遲）", "資料時間",
    "資料來源", "當日成交量", "融資維持率", "方向", "多方評分",
    "空方評分", "買進觸發", "買進區間", "最高接受價",
    "停損／失效", "目標一", "目標二", "加碼條件",
    "成本後RR", "分類", "現在動作", "模型／驗證狀態",
    "加碼價格", "停利價格",
)


def project_required_fields(row):
    """Never call an old snapshot fresh or infer strategy/score values."""
    fields = {key: None for key in REQUIRED_INFORMATION_COLUMNS}
    is_fresh = row.get("data_status") == "FRESH_EXECUTED_TRADE"
    fields.update({
        "股票代碼": row.get("symbol"),
        "股票名稱": row.get("name"),
        "即時價": row.get("last_price") if is_fresh else None,
        "最近觀察價（可能延遲）": row.get("last_price"),
        "資料時間": row.get("last_trade_time") or row.get("snapshot_observed_at"),
        "資料來源": row.get("source"),
        "當日成交量": row.get("volume"),
        "方向": "待確認",
        "分類": "X",
        "現在動作": "禁止交易",
        "模型／驗證狀態": "僅資訊觀察／未驗證通過",
    })
    return fields


def build(universe, snapshots, checked_at, errors=None):
    by_exchange = {"TWSE": {}, "TPEx": {}}
    statuses = {"TWSE": "MISSING", "TPEx": "MISSING"}
    expected_tib = {
        str(meta["symbol"]) for meta in universe
        if meta.get("exchange") == "TWSE" and expected_snapshot_market(meta) == INNOVATION_BOARD
    }
    tib_payload = snapshots.get(INNOVATION_BOARD)
    tib_valid = isinstance(tib_payload, dict) and isinstance(tib_payload.get("data"), list)
    for exchange, market in MARKET.items():
        data = snapshots.get(market)
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            statuses[exchange] = "RETURNED"
        # TIB must be fetched independently; do not treat its absence as TSE success.
        for source_market in ((market, INNOVATION_BOARD) if exchange == "TWSE" and expected_tib else (market,)):
            source = snapshots.get(source_market)
            if isinstance(source, dict) and isinstance(source.get("data"), list):
                for q in source["data"]:
                    if isinstance(q, dict):
                        code = str(q.get("symbol") or "")
                        if code and (source_market != INNOVATION_BOARD or code in expected_tib):
                            by_exchange[exchange][code] = (q, str(source.get("date") or ""), source_market)
    if expected_tib and not tib_valid:
        statuses["TWSE"] = "PARTIAL_TIB_MISSING" if statuses["TWSE"] == "RETURNED" else "MISSING_TSE_AND_TIB"
    # Snapshot diagnostics are informational; never certify executed-trade coverage.
    official_sets = {
        exchange: {str(meta["symbol"]) for meta in universe
                   if meta.get("exchange") == exchange}
        for exchange in MARKET
    }
    snapshot_integrity = {}
    for exchange, market in MARKET.items():
        payload = snapshots.get(market)
        raw = payload.get("data") if isinstance(payload, dict) else None
        raw = list(raw) if isinstance(raw, list) else []
        if exchange == "TWSE" and expected_tib and tib_valid:
            # Keep raw duplicate/unknown diagnostics; TSE and TIB have distinct markets.
            raw.extend(tib_payload["data"])
        symbols = [str(q.get("symbol") or "") for q in raw if isinstance(q, dict)]
        present = set(symbols) & official_sets[exchange]
        tib_symbols = {str(q.get("symbol") or "") for q in (tib_payload.get("data") or []) if isinstance(q, dict)} if tib_valid else set()
        tse_data = snapshots.get("TSE") if exchange == "TWSE" else None
        tse_symbols = {str(q.get("symbol") or "") for q in (tse_data.get("data") or []) if isinstance(q, dict)} if isinstance(tse_data, dict) else set()
        missing_tib_endpoint = expected_tib - tib_symbols
        found_in_tse_not_tib = missing_tib_endpoint & tse_symbols
        snapshot_integrity[exchange] = {
            "api_response_valid": statuses[exchange] == "RETURNED",
            "raw_rows": len(raw),
            "unique_returned_symbols": len(set(symbols) - {""}),
            "duplicate_symbol_rows": len(symbols) - len(set(symbols) - {""})
                - symbols.count(""),
            "blank_symbol_rows": symbols.count(""),
            "unexpected_symbols": len(set(symbols) - {""} - official_sets[exchange]),
            "official_symbols_missing_from_snapshot": len(official_sets[exchange] - present),
            "official_symbol_coverage_pct": round(
                100 * len(present) / len(official_sets[exchange]), 2
            ) if official_sets[exchange] else 0.0,
            "snapshot_date": payload.get("date") if isinstance(payload, dict) else None,
            "snapshot_time_is_execution_time": False,
            "innovation_board_market": INNOVATION_BOARD if exchange == "TWSE" else None,
            "innovation_board_official_count": len(expected_tib) if exchange == "TWSE" else 0,
            "innovation_board_api_response_valid": tib_valid if exchange == "TWSE" and expected_tib else None,
            "innovation_board_missing_count": len(expected_tib - (tib_symbols | tse_symbols)) if exchange == "TWSE" else 0,
            "innovation_board_missing_from_tib_endpoint_count": len(missing_tib_endpoint) if exchange == "TWSE" else 0,
            "innovation_board_found_in_tse_not_tib": sorted(found_in_tse_not_tib) if exchange == "TWSE" else [],
            "missing_official_symbols": [
                {"symbol": str(meta["symbol"]), "name": str(meta.get("name") or ""),
                 "classification": "NOT_RETURNED_BY_FUGLE_SNAPSHOT",
                 "next_check": "FUGLE_TICKER_PRODUCT_TYPE_AND_LISTING_STATUS"}
                for meta in universe
                if meta.get("exchange") == exchange
                and str(meta["symbol"]) not in present
            ],
        }
    rows = []
    for meta in universe:
        exchange = meta.get("exchange")
        if exchange not in MARKET:
            continue
        q, date, source_market = by_exchange[exchange].get(str(meta["symbol"]), (None, "", None))
        row = record(meta, q, date, checked_at)
        row["snapshot_market_source"] = source_market
        if source_market:
            row["market"] = source_market
        row["required_fields"] = project_required_fields(row)
        rows.append(row)
    eligible = [x for x in rows if x["last_price"] is not None and x["last_price"] <= 100]
    candidates = sorted(
        eligible, key=lambda x: (
            x["change_pct"] is not None, x["change_pct"] if x["change_pct"] is not None else float("-inf"),
            x["volume"] if x["volume"] is not None else -1,
        ), reverse=True)
    by_market = {}
    for exchange in MARKET:
        subset = [x for x in rows if x["exchange"] == exchange]
        by_market[exchange] = {
            "universe": len(subset),
            "snapshot_rows": sum(x["source"] != "NO_SNAPSHOT_ROW" for x in subset),
            "fresh_executed": sum(x["data_status"] == "FRESH_EXECUTED_TRADE" for x in subset),
            "observed_price": sum(x["last_price"] is not None for x in subset),
            "snapshot_reference_without_trade_time": sum(
                x["last_price"] is not None and x["last_trade_time"] is None
                for x in subset),
        }
        by_market[exchange]["fresh_executed_pct"] = round(
            100 * by_market[exchange]["fresh_executed"] / len(subset), 1) if subset else 0.0
    verified = sum(x["data_status"] == "FRESH_EXECUTED_TRADE" for x in rows)
    report = {
        "schema": "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1",
        "checked_at_tpe": checked_at.isoformat(),
        "universe_count": len(rows), "snapshot_status": statuses,
        "snapshot_errors": errors or {}, "by_exchange": by_market,
        "snapshot_integrity": snapshot_integrity,
        "snapshot_api_calls_expected_per_scan": 3 if expected_tib else 2,
        "individual_quote_calls_are_bounded_separately": True,
        "observed_price_count": sum(x["last_price"] is not None for x in rows),
        "snapshot_reference_requires_last_trade_time": False,
        "snapshot_reference_without_trade_time_count": sum(
            x["last_price"] is not None and x["last_trade_time"] is None
            for x in rows),
        "fresh_executed_count": verified,
        "fresh_executed_pct": round(100 * verified / len(rows), 1) if rows else 0.0,
        "priced_under_100_count": len(eligible),
        "ranked_observations": candidates[:100],
        "all_symbols": rows,
        "required_information_columns": list(REQUIRED_INFORMATION_COLUMNS),
        "missing_field_label": "待確認（未有可驗證資料）",
        "observation_mode": "RESEARCH_INFORMATION_ONLY",
        "trade_decision": "🔴 禁止新進場、未驗證通過",
        "no_order_or_production_promotion": True,
        "note": ("All official universe symbols are included. Rankings use observed "
                 "snapshot prices and are NOT certified market-wide live ranks. "
                 "Unverified and stale observations are labelled per symbol. "
                 "No model inference, entry, target, or score is fabricated."),
    }
    return report


ALERT_COLUMNS = (
    "股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分",
    "空方評分", "買進觸發", "最高接受價", "停損／失效",
    "現在動作", "加碼價格", "停利價格",
)


def alert_row(row):
    """13-column presentation, preserving observed but unverified price provenance."""
    fields = row.get("required_fields") or project_required_fields(row)
    fresh = row.get("data_status") == "FRESH_EXECUTED_TRADE"
    price = row.get("last_price")
    shown_price = f"{price:.2f}" if fresh and price is not None else "待確認"
    if price is not None and not fresh:
        shown_price += f"（觀察價 {price:.2f}，未驗證）"
    return [
        fields.get("股票代碼") or "—",
        fields.get("股票名稱") or "待確認",
        shown_price,
        fields.get("分類") or "X",
        fields.get("方向") or "待確認",
        fields.get("多方評分") if fields.get("多方評分") is not None else "—",
        fields.get("空方評分") if fields.get("空方評分") is not None else "—",
        fields.get("買進觸發") or "待確認",
        fields.get("最高接受價") or "待確認",
        fields.get("停損／失效") or "待確認",
        "等待",
        fields.get("加碼價格") or "待確認",
        fields.get("停利價格") or "待確認",
    ]


def summary(report):
    lines = [
        "# Sky 警戒｜全市場資訊觀察（非正式交易訊號）", "",
        f"查詢時間：{report['checked_at_tpe']}",
        f"官方母池：{report['universe_count']} 檔；有價格觀察：{report['observed_price_count']} 檔",
        f"其中無逐筆成交時間仍保留觀察價：{report['snapshot_reference_without_trade_time_count']} 檔",
        f"逐檔新鮮成交驗證：{report['fresh_executed_count']} 檔（{report['fresh_executed_pct']:.1f}%）",
        f"價格 ≤100 元的觀察名單：{report['priced_under_100_count']} 檔", "",
        "| 市場 | 母池 | 快照代號 | 有價格 | 新鮮成交 | 覆蓋率 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for exchange, label in (("TWSE", "上市"), ("TPEx", "上櫃")):
        x = report["by_exchange"][exchange]
        lines.append(f"| {label} | {x['universe']} | {x['snapshot_rows']} | "
                     f"{x['observed_price']} | {x['fresh_executed']} | {x['fresh_executed_pct']:.1f}% |")
    lines += [
        "", "## 警戒資訊表（13 欄；觀察價格非驗證即時價）",
        "| " + " | ".join(ALERT_COLUMNS) + " |",
        "| " + " | ".join(["---"] * len(ALERT_COLUMNS)) + " |",
    ]
    rows = report.get("ranked_observations") or []
    if not rows:
        lines.append("| — | 暫無可用價格觀察 | 待確認 | X | 不交易 | — | — | 待確認 | 待確認 | 待確認 | 等待 | 待確認 | 待確認 |")
    for row in rows:
        vals = alert_row(row)
        lines.append("| " + " | ".join(str(v).replace("|", "／").replace("\n", " ") for v in vals) + " |")
    lines += [
        "", "警戒排序僅依可取得的觀察價／漲幅／成交量，不等於多方評分、正式警戒訊號或經驗證全市場即時排名。",
        "完整股票母池、資料時間、成交量、來源、缺值與狀態詳見 full_universe.json。",
        "缺少模型推論或驗證證據時，方向、評分、觸發、加碼與停利不得推測。",
        "", f"**{report['trade_decision']}**",
        "研究資訊持續呈現；交易由使用者自行判斷，系統不自動下單。",
    ]
    return "\n".join(lines) + "\n"


def main():
    checked_at = datetime.now(TZ)
    universe, status = load_official_universe()
    snapshots = {}
    errors = {}
    innovation_count = sum(expected_snapshot_market(meta) == INNOVATION_BOARD for meta in universe)
    for market in list(MARKET.values()) + ([INNOVATION_BOARD] if innovation_count else []):
        try:
            snapshots[market] = snapshot_quotes(market)
        except Exception as exc:
            errors[market] = type(exc).__name__
    report = build(universe, snapshots, checked_at, errors)
    report["official_universe_warnings"] = status.get("warnings", [])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "full_universe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "latest.md").write_text(summary(report), encoding="utf-8")
    print(f"Sky information scan: universe={report['universe_count']} "
          f"observed={report['observed_price_count']} "
          f"fresh={report['fresh_executed_count']} "
          f"trade_decision=NO_TRADE")
    if not universe:
        raise SystemExit("OFFICIAL_UNIVERSE_UNAVAILABLE")


if __name__ == "__main__":
    main()
