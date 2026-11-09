"""Independent Fugle-only whole-market information scanner (research-only).

No TWSE MIS, no legacy scanner, no inferred execution timestamps, no orders.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from src.fugle import get_tickers, snapshot_quotes
from src.official import load_official_universe
from src.realtime_quote_evidence import timestamp_tpe

TZ = ZoneInfo("Asia/Taipei")
MARKETS = {"TSE": "TWSE", "OTC": "TPEx"}
SYMBOL = re.compile(r"^[1-9][0-9]{3}$")
COLUMNS = ("股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分",
           "空方評分", "買進觸發", "最高接受價", "停損／失效",
           "現在動作", "加碼價格", "停利價格")


def positive(value):
    try:
        n = float(value)
        return n if math.isfinite(n) and n > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def items(payload, *, source):
    if not isinstance(payload, dict):
        raise ValueError(f"{source}: expected JSON object")
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ValueError(f"{source}: missing data list")
    return rows


def universe_from_tickers(payloads, snapshots=None):
    """Use paid tickers first, with explicitly uncertified paid snapshot fallback."""
    universe = {}
    basis = {}
    snapshots = snapshots or {}
    for market, exchange in MARKETS.items():
        ticker_rows = items(payloads.get(market), source=f"tickers:{market}")
        ticker_count = 0
        for row in ticker_rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "").strip()
            if SYMBOL.fullmatch(symbol) and str(row.get("type") or "EQUITY").upper() in ("EQUITY", "COMMONSTOCK"):
                universe[symbol] = {"symbol": symbol, "name": row.get("name") or "",
                                    "exchange": exchange, "market": market,
                                    "universe_source": "FUGLE_PAID_TICKERS"}
                ticker_count += 1
        fallback_count = 0
        if ticker_count == 0 and isinstance(snapshots.get(market), dict):
            for row in items(snapshots[market], source=f"snapshot:{market}"):
                if not isinstance(row, dict):
                    continue
                symbol = str(row.get("symbol") or "").strip()
                if not SYMBOL.fullmatch(symbol):
                    continue
                if symbol in universe and universe[symbol]["market"] != market:
                    raise ValueError("cross_market_symbol_collision")
                universe[symbol] = {"symbol": symbol, "name": row.get("name") or "",
                                    "exchange": exchange, "market": market,
                                    "universe_source": "FUGLE_PAID_SNAPSHOT_FALLBACK"}
                fallback_count += 1
        basis[exchange] = {"ticker_symbols": ticker_count,
                           "snapshot_fallback_symbols": fallback_count,
                           "ticker_universe_available": ticker_count > 0}
    if not universe or any(not any(x["market"] == m for x in universe.values()) for m in MARKETS):
        raise ValueError(f"NO_BOTH_MARKETS_FUGLE_UNIVERSE: {basis}")
    return universe, basis


def classify(meta, quote, source_date, checked):
    result = {**meta, "source": "Fugle paid bulk snapshot" if quote is not None else "NO_SNAPSHOT_ROW",
              "data_status": "MISSING_QUOTE", "last_price": None, "volume": None,
              "last_trade_time": None, "research_only": True, "production_eligible": False}
    if not isinstance(quote, dict):
        return result
    trade = quote.get("lastTrade")
    trade = trade if isinstance(trade, dict) else {}
    price = positive(trade.get("price")) or positive(quote.get("lastPrice"))
    result["last_price"] = price
    result["volume"] = positive(quote.get("tradeVolume"))
    # Never use closeTime, lastUpdated, quote timestamp or response clock as execution proof.
    stamp = timestamp_tpe(trade.get("time")) if trade.get("time") else None
    if stamp:
        result["last_trade_time"] = stamp.isoformat()
    within_session = checked.weekday() < 5 and time(9, 0) <= checked.time() <= time(13, 30)
    if source_date != checked.date().isoformat():
        result["data_status"] = "SNAPSHOT_DATE_NOT_TODAY"
    elif price is None:
        result["data_status"] = "MISSING_EXECUTED_PRICE"
    elif quote.get("isTrial") is True:
        result["data_status"] = "TRIAL_QUOTE"
    elif stamp is None:
        result["data_status"] = "UNVERIFIED_EXECUTION_TIME"
    elif not within_session:
        result["data_status"] = "OUTSIDE_MARKET_SESSION"
    elif stamp.date() != checked.date() or not (-30 <= (checked - stamp).total_seconds() <= 180):
        result["data_status"] = "STALE_OR_INVALID_EXECUTION_TIME"
    else:
        result["data_status"] = "FRESH_EXECUTED_TRADE"
    return result


def scan(*, now=None, ticker_fetch=get_tickers, snapshot_fetch=snapshot_quotes,
         official_fetch=load_official_universe):
    checked = now or datetime.now(TZ)
    if checked.tzinfo is None:
        raise ValueError("naive check time not allowed")
    checked = checked.astimezone(TZ)
    ticker_payloads, snapshot_payloads, errors = {}, {}, {}
    for market in MARKETS:
        try:
            ticker_payloads[market] = ticker_fetch(market)
        except Exception as exc:
            errors[f"tickers_{market}"] = type(exc).__name__
        try:
            snapshot_payloads[market] = snapshot_fetch(market)
        except Exception as exc:
            errors[f"snapshot_{market}"] = type(exc).__name__
    if len(ticker_payloads) != 2:
        raise RuntimeError(f"FUGLE_TICKER_UNIVERSE_UNAVAILABLE: {errors}")
    diagnostic = {}
    for market, payload in ticker_payloads.items():
        raw = payload.get("data") if isinstance(payload, dict) else None
        raw = raw if isinstance(raw, list) else []
        diagnostic[market] = {
            "payload_keys": sorted(str(k) for k in payload.keys()) if isinstance(payload, dict) else [],
            "returned": len(raw),
            "valid_4digit": sum(
                bool(SYMBOL.fullmatch(str(x.get("symbol") or "")))
                for x in raw if isinstance(x, dict)),
            "first_row_keys": sorted(str(k) for k in raw[0].keys()) if raw and isinstance(raw[0], dict) else [],
            "first_row_type": str(raw[0].get("type")) if raw and isinstance(raw[0], dict) else None,
        }
    print("FUGLE_TICKER_DIAGNOSTIC", json.dumps(diagnostic, ensure_ascii=False), flush=True)
    snapshot_diag = {}
    for market, payload in snapshot_payloads.items():
        raw = payload.get("data") if isinstance(payload, dict) else None
        snapshot_diag[market] = {"date": str(payload.get("date") or "") if isinstance(payload, dict) else "",
                                 "returned": len(raw) if isinstance(raw, list) else None}
    print("FUGLE_SNAPSHOT_DIAGNOSTIC", json.dumps(snapshot_diag, ensure_ascii=False), flush=True)
    fugle_universe, universe_basis = universe_from_tickers(ticker_payloads, snapshot_payloads)
    official_raw, official_status = official_fetch()
    if not isinstance(official_raw, list) or not isinstance(official_status, dict):
        raise RuntimeError("OFFICIAL_UNIVERSE_INVALID")
    official_by_exchange = {}
    for meta in official_raw:
        if not isinstance(meta, dict):
            continue
        symbol = str(meta.get("symbol") or "").strip()
        exchange = meta.get("exchange")
        if SYMBOL.fullmatch(symbol) and exchange in ("TWSE", "TPEx"):
            key = (exchange, symbol)
            if key in official_by_exchange:
                raise RuntimeError("OFFICIAL_UNIVERSE_DUPLICATE")
            official_by_exchange[key] = {
                "symbol": symbol, "name": meta.get("name") or "",
                "exchange": exchange, "market": "TSE" if exchange == "TWSE" else "OTC",
                "universe_source": meta.get("universe_source") or "OFFICIAL"}
    if not any(x["exchange"] == "TWSE" for x in official_by_exchange.values()) or not any(
        x["exchange"] == "TPEx" for x in official_by_exchange.values()
    ):
        raise RuntimeError("OFFICIAL_BOTH_MARKETS_REQUIRED")
    if official_status.get("warnings"):
        raise RuntimeError("OFFICIAL_UNIVERSE_WARNINGS")
    universe = {x["symbol"]: x for x in official_by_exchange.values()}
    if len(universe) != len(official_by_exchange):
        raise RuntimeError("OFFICIAL_SYMBOL_COLLISION")
    fugle_keys = {(x["exchange"], x["symbol"]) for x in fugle_universe.values()}
    official_keys = set(official_by_exchange)
    universe_diff = {
        "official_not_in_fugle": [
            {"exchange": exchange, "symbol": symbol}
            for exchange, symbol in sorted(official_keys - fugle_keys)],
        "fugle_not_in_official": [
            {"exchange": exchange, "symbol": symbol}
            for exchange, symbol in sorted(fugle_keys - official_keys)],
        "official_universe": len(official_keys),
        "fugle_universe": len(fugle_keys),
    }
    print("UNIVERSE_DIFF", json.dumps({
        "official_universe": len(official_keys),
        "fugle_universe": len(fugle_keys),
        "official_not_in_fugle": len(official_keys - fugle_keys),
        "fugle_not_in_official": len(fugle_keys - official_keys)
    }, ensure_ascii=False), flush=True)
    by_market = {}
    rows = []
    for market, exchange in MARKETS.items():
        payload = snapshot_payloads.get(market)
        snap_rows = {}
        date = None
        if payload is not None:
            date = str(payload.get("date") or "") if isinstance(payload, dict) else ""
            for q in items(payload, source=f"snapshot:{market}"):
                if isinstance(q, dict) and str(q.get("symbol") or "") in universe:
                    symbol = str(q["symbol"])
                    if universe[symbol]["market"] == market:
                        snap_rows[symbol] = q
        matched = [m for m in universe.values() if m["market"] == market]
        market_rows = [classify(m, snap_rows.get(m["symbol"]), date, checked) for m in matched]
        rows.extend(market_rows)
        by_market[exchange] = {
            "universe": len(matched), "snapshot_rows": sum(x["source"] != "NO_SNAPSHOT_ROW" for x in market_rows),
            "observed_price": sum(x["last_price"] is not None for x in market_rows),
            "fresh_executed": sum(x["data_status"] == "FRESH_EXECUTED_TRADE" for x in market_rows),
        }
    rows.sort(key=lambda x: (x["exchange"], x["symbol"]))
    report = {
        "schema": "SKY_FUGLE_INDEPENDENT_MARKET_SCAN_V1",
        "checked_at_tpe": checked.isoformat(), "source": "Fugle paid API tickers+snapshot",
        "universe_count": len(rows), "observed_price_count": sum(x["last_price"] is not None for x in rows),
        "fresh_executed_count": sum(x["data_status"] == "FRESH_EXECUTED_TRADE" for x in rows),
        "by_exchange": by_market, "universe_basis": universe_basis,
        "universe_comparison": universe_diff,
        "full_market_universe_certified": True,
        "full_market_executed_certified": False,
        "errors": errors, "all_symbols": rows,
        "official_universe_status": official_status,
        "production_eligible": False, "trade_decision": "禁止交易",
        "note": "Snapshot observation is not certified executed-live. No AI inference or trade permission.",
    }
    return report


def render(report):
    lines = ["# Sky 全市場新掃描｜富果獨立資訊版", "",
             f"資料查詢時間：{report['checked_at_tpe']}；資料來源：{report['source']}",
             f"母池：{report['universe_count']}；觀察價：{report['observed_price_count']}；"
             f"最新成交時間驗證：{report['fresh_executed_count']}", "",
             "| " + " | ".join(COLUMNS) + " |", "| " + " | ".join("---" for _ in COLUMNS) + " |"]
    detail_rows = []
    for item in report["all_symbols"]:
        fresh = item["data_status"] == "FRESH_EXECUTED_TRADE"
        price = item["last_price"]
        displayed = f"{price:.2f}" if fresh and price is not None else (
            f"待確認（觀察價 {price:.2f}，未驗證）" if price is not None else "待確認")
        vals = [item["symbol"], item["name"] or "待確認", displayed, "X", "不交易",
                "—", "—", "待確認", "待確認", "待確認", "禁止交易", "待確認", "待確認"]
        lines.append("| " + " | ".join(str(x).replace("|", "／").replace("\n", " ") for x in vals) + " |")
        detail_rows.append({**dict(zip(COLUMNS, vals)), "資料來源": item["source"],
                            "資料時間": item["last_trade_time"], "資料狀態": item["data_status"],
                            "成交量": item["volume"], "正式交易資格": False})
    lines.extend(["", "官方母池完整性認證：" + str(report["full_market_universe_certified"]),
                  "🔴 僅資訊觀察；不包含 AI 多空評分、買賣點或正式交易授權。"])
    return "\n".join(lines) + "\n", detail_rows


def main():
    output = Path("output/sky_fugle_independent")
    output.mkdir(parents=True, exist_ok=True)
    report = scan()
    markdown, rows = render(report)
    (output / "full_universe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "latest_13col.json").write_text(json.dumps({
        "schema": "SKY_FUGLE_INDEPENDENT_13COL_V1", "checked_at_tpe": report["checked_at_tpe"],
        "columns": list(COLUMNS), "rows": rows, "production_eligible": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "latest_13col.md").write_text(markdown, encoding="utf-8")
    if len(rows) != report["universe_count"] or len({r["股票代碼"] for r in rows}) != len(rows):
        raise RuntimeError("INCOMPLETE_OR_DUPLICATE_13COL_REPORT")
    if any(row["正式交易資格"] is not False for row in rows):
        raise RuntimeError("INVALID_PRODUCTION_PERMISSION")
    print(json.dumps({"status": "INFORMATION_ONLY", "universe": report["universe_count"],
                      "observed": report["observed_price_count"],
                      "fresh": report["fresh_executed_count"],
                      "errors": report["errors"],
                      "universe_diff": {key: len(report["universe_comparison"][key])
                                        for key in ("official_not_in_fugle", "fugle_not_in_official")}}, ensure_ascii=False))
    if report["errors"]:
        raise RuntimeError("PARTIAL_FUGLE_SOURCE_ERRORS")


if __name__ == "__main__":
    main()
