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
        "exchange": meta["exchange"], "market": MARKET[meta["exchange"]],
        "source": "Fugle paid bulk snapshot" if payload is not None else "NO_SNAPSHOT_ROW",
        "data_status": "MISSING_QUOTE", "last_price": None,
        "change_pct": None, "volume": None, "last_trade_time": None,
        "time_age_seconds": None, "research_only": True,
        "production_eligible": False, "trade_signal": False,
    }
    if not isinstance(payload, dict):
        return result
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
    ts = timestamp_tpe(trade.get("time") or payload.get("closeTime"))
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
        "資料時間": row.get("last_trade_time"),
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
    for exchange, market in MARKET.items():
        data = snapshots.get(market)
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            statuses[exchange] = "RETURNED"
            for q in data["data"]:
                if isinstance(q, dict):
                    code = str(q.get("symbol") or "")
                    if code:
                        by_exchange[exchange][code] = (q, str(data.get("date") or ""))
    rows = []
    for meta in universe:
        exchange = meta.get("exchange")
        if exchange not in MARKET:
            continue
        q, date = by_exchange[exchange].get(str(meta["symbol"]), (None, ""))
        row = record(meta, q, date, checked_at)
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
        }
        by_market[exchange]["fresh_executed_pct"] = round(
            100 * by_market[exchange]["fresh_executed"] / len(subset), 1) if subset else 0.0
    verified = sum(x["data_status"] == "FRESH_EXECUTED_TRADE" for x in rows)
    report = {
        "schema": "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1",
        "checked_at_tpe": checked_at.isoformat(),
        "universe_count": len(rows), "snapshot_status": statuses,
        "snapshot_errors": errors or {}, "by_exchange": by_market,
        "observed_price_count": sum(x["last_price"] is not None for x in rows),
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


def summary(report):
    lines = [
        "# Sky 快掃｜全市場資訊觀察（非正式交易訊號）", "",
        f"查詢時間：{report['checked_at_tpe']}",
        f"官方母池：{report['universe_count']} 檔；有價格觀察：{report['observed_price_count']} 檔",
        f"逐檔新鮮成交驗證：{report['fresh_executed_count']} 檔（{report['fresh_executed_pct']:.1f}%）",
        f"價格 ≤100 元的觀察名單：{report['priced_under_100_count']} 檔", "",
        "| 市場 | 母池 | 快照代號 | 有價格 | 新鮮成交 | 覆蓋率 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for exchange, label in (("TWSE", "上市"), ("TPEx", "上櫃")):
        x = report["by_exchange"][exchange]
        lines.append(f"| {label} | {x['universe']} | {x['snapshot_rows']} | "
                     f"{x['observed_price']} | {x['fresh_executed']} | {x['fresh_executed_pct']:.1f}% |")
    # User-facing contract: always render the same 13 columns, including when
    # verification blocks new entries. Never substitute stale observed prices
    # for a verified real-time trade, nor fabricate strategy levels or scores.
    columns = (
        "股票代碼", "股票名稱", "即時價", "分類", "方向",
        "多方評分", "空方評分", "買進觸發", "最高接受價",
        "停損／失效", "現在動作", "加碼價格", "停利價格",
    )
    lines += ["", "## 全市場股票資訊（正式交易未驗證，僅資訊觀察）",
              "| " + " | ".join(columns) + " |",
              "| " + " | ".join("---" for _ in columns) + " |"]
    displayed = report["ranked_observations"][:30]
    for row in displayed:
        confirmed = row["data_status"] == "FRESH_EXECUTED_TRADE"
        price = f"{row['last_price']:.2f}" if confirmed else "待確認"
        values = (
            row["symbol"], row["name"], price, "X", "不交易",
            "—", "—", "待確認", "待確認", "待確認",
            "觀察", "待確認", "待確認",
        )
        lines.append("| " + " | ".join(str(value).replace("|", "／") for value in values) + " |")
    if not displayed:
        lines.append("| — | 暫無合格候選 | 待確認 | X | 不交易 | — | — | 待確認 | 待確認 | 待確認 | 等待 | 待確認 | 待確認 |")
    lines += [
        "",
        "## 觀察價與成交時間（可能延遲；不得視為即時價）",
        "| 股票代碼 | 最近觀察價 | 成交時間 | 資料狀態 |",
        "|---|---:|---|---|",
    ]
    for row in displayed:
        observed = f"{row['last_price']:.2f}" if row["last_price"] is not None else "待確認"
        timestamp = row.get("last_trade_time") or "待確認"
        lines.append(f"| {row['symbol']} | {observed} | {timestamp} | {row['data_status']} |")
    lines += [
        "",
        "以上只列前 30 筆價格觀察，不代表全市場排名或交易候選。"
        "其餘完整母池、資料時間與缺漏原因詳見 full_universe.json。",
        "多空評分、買進／加碼／停損／停利價：未有通過驗證的策略輸出時保持待確認。",
        "",
        f"**{report['trade_decision']}**",
        "資訊仍提供；最終交易選擇由使用者自行決定。",
    ]
    return "\n".join(lines) + "\n"


def main():
    checked_at = datetime.now(TZ)
    universe, status = load_official_universe()
    snapshots = {}
    errors = {}
    for market in MARKET.values():
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
