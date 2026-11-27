"""W0 #363: bounded, explicitly opted-in Fugle 5m/trades evidence collector.

Research-source evidence only, never trade approval. No retries or scheduling.
No reliance on quote refresh time as executed-trade time.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import fugle
from .sky_single_stock_realtime import timestamp_tpe

TPE = timezone(timedelta(hours=8))
MAX_TRADES_PAGES = 5
PAGE_LIMIT = 500


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    val = float(value)
    return val if math.isfinite(val) and val >= 0 else None


def analyze(symbol, quote, candles, pages, *, observed_at=None):
    """Offline, independently replayable conservative source contract."""
    now = observed_at or datetime.now(TPE)
    out = {
        "schema": "SKY_5M_TRADES_BOUND_SOURCE_V1",
        "symbol": symbol, "source": "Fugle MarketData API",
        "observed_at_tpe": now.astimezone(TPE).isoformat(),
        "quote_status": "HOLD", "five_minute_status": "HOLD",
        "trades_status": "HOLD", "volume_status": "HOLD",
        "vwap_status": "HOLD", "execution_authorized": False,
        "production_eligible": False, "automatic_order": False,
        "max_pages": MAX_TRADES_PAGES,
    }
    if not isinstance(quote, dict) or not isinstance(candles, dict):
        return out
    if not symbol.isascii() or not symbol.isdigit() or len(symbol) not in (4, 5, 6):
        return out
    date = now.astimezone(TPE).date().isoformat()
    trade = quote.get("lastTrade")
    trade = trade if isinstance(trade, dict) else {}
    time_str = timestamp_tpe(trade.get("time"))
    if quote.get("date") == date and time_str and _number(trade.get("price")) not in (None, 0):
        try:
            t = datetime.fromisoformat(time_str)
            if t.date().isoformat() == date and t <= now:
                out["quote_status"] = "PASS_ACTUAL_LAST_TRADE_REFERENCE"
                out["last_trade_tpe"] = time_str
                out["last_trade_price"] = trade["price"]
        except (TypeError, ValueError):
            pass
    raw = candles.get("data")
    if isinstance(raw, list) and raw and len(raw) <= 100:
        parsed = []
        seen = set()
        valid = True
        for row in raw:
            if not isinstance(row, dict):
                valid = False
                break
            stamp = row.get("date")
            try:
                dt = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(TPE)
                if not isinstance(stamp, str) or dt.utcoffset() is None:
                    raise ValueError("invalid timezone")
            except (ValueError, TypeError, AttributeError):
                valid = False
                break
            prices = [_number(row.get(f)) for f in ("open", "high", "low", "close")]
            vol = _number(row.get("volume"))
            if (dt.date().isoformat() != date or dt.hour < 9 or (dt.hour == 13 and dt.minute > 30)
                    or dt.hour > 13 or dt.minute % 5 or dt.second
                    or dt.isoformat() in seen
                    or None in prices or min(prices) <= 0
                    or not prices[2] <= min(prices[0], prices[3])
                    or not max(prices[0], prices[3]) <= prices[1] or vol is None):
                valid = False
                break
            seen.add(dt.isoformat())
            parsed.append((dt, row))
        if valid and all(a[0] < b[0] for a, b in zip(parsed, parsed[1:])):
            completed = [(d, row) for d, row in parsed if d + timedelta(minutes=5) <= now]
            out["five_minute_status"] = ("PASS_COMPLETED_BARS_OBSERVED" if completed
                                          else "HOLD_NO_COMPLETED_BARS")
            out["returned_bar_count"] = len(parsed)
            out["completed_bar_count"] = len(completed)
            out["excluded_incomplete_bar_count"] = len(parsed) - len(completed)
            out["completed_bar_volume_raw_sum"] = sum(float(row["volume"]) for _, row in completed)
            out["last_completed_bar_start"] = completed[-1][0].isoformat() if completed else None
            out["five_minute_raw"] = raw
    # Trades pagination requires an empty terminal page and stable provenance.
    # Even a complete sequential fetch cannot by itself prove point-in-time
    # atomicity while new trades are being inserted.
    if isinstance(pages, list) and pages:
        serials = set()
        total_size = 0
        total_value = 0.0
        terminal = False
        valid = True
        for index, page in enumerate(pages):
            if not isinstance(page, dict) or page.get("offset") != index * PAGE_LIMIT:
                valid = False
                break
            data = page.get("data")
            if not isinstance(data, list) or len(data) > PAGE_LIMIT:
                valid = False
                break
            if not data:
                terminal = index == len(pages) - 1
                break
            for row in data:
                if not isinstance(row, dict):
                    valid = False
                    break
                serial = row.get("serial")
                stamp = timestamp_tpe(row.get("time"))
                size, price = _number(row.get("size")), _number(row.get("price"))
                if (type(serial) is not int or serial in serials or not stamp
                        or size is None or int(size) != size or size <= 0
                        or price is None or price <= 0):
                    valid = False
                    break
                dt = datetime.fromisoformat(stamp)
                if dt.date().isoformat() != date or dt > now:
                    valid = False
                    break
                serials.add(serial)
                if serial == 99999999 and dt.hour == 14 and dt.minute == 30:
                    continue
                if dt.hour < 9 or dt.hour > 13 or (dt.hour == 13 and dt.minute > 30):
                    valid = False
                    break
                total_size += int(size)
                total_value += price * int(size)
            if not valid:
                break
        out["trades_page_count"] = len(pages)
        out["trades_terminal_empty_page"] = terminal
        out["trades_raw_pages"] = pages
        if valid and terminal and total_size:
            out["trades_status"] = "PASS_PAGED_RESEARCH_ARITHMETIC_ONLY"
            out["trades_sum_raw_size"] = total_size
            out["trades_weighted_mean_research"] = round(total_value / total_size, 6)
            quote_volume = _number((quote.get("total") or {}).get("tradeVolume"))
            out["quote_volume_raw"] = quote_volume
            if quote_volume == total_size:
                out["volume_status"] = "RECONCILED_SAME_SNAPSHOT_NOT_CROSS_SOURCE_CERTIFIED"
            out["vwap_status"] = "RESEARCH_ONLY_NO_ATOMIC_PIT_PROOF"
    out["five_minute_source_certified_for_trading"] = False
    out["volume_unit_cross_source_certified"] = False
    out["independent_vwap_certified"] = False
    return out


def collect(symbol, *, max_pages=MAX_TRADES_PAGES):
    if not symbol.isascii() or not symbol.isdigit() or len(symbol) not in (4, 5, 6):
        raise ValueError("INVALID_SYMBOL")
    if type(max_pages) is not int or max_pages < 1 or max_pages > MAX_TRADES_PAGES:
        raise ValueError("INVALID_BOUNDED_PAGE_COUNT")
    now = datetime.now(TPE)
    result = {
        "schema": "SKY_5M_TRADES_BOUND_SOURCE_V1", "symbol": symbol,
        "observed_at_tpe": now.isoformat(), "five_minute_status": "HOLD",
        "trades_status": "HOLD", "vwap_status": "HOLD",
        "execution_authorized": False, "automatic_order": False,
        "production_eligible": False,
    }
    try:
        quote = fugle.get_quote(symbol)
        candles = fugle.get_candles(symbol, timeframe="5")
        pages = []
        for offset in range(0, max_pages * PAGE_LIMIT, PAGE_LIMIT):
            page = fugle.get_trades(symbol, offset=offset, limit=PAGE_LIMIT)
            data = page.get("data") if isinstance(page, dict) else None
            if not isinstance(data, list):
                raise ValueError("INVALID_TRADES_RESPONSE")
            pages.append({"offset": offset, "data": data})
            if not data:
                break
        result = analyze(symbol, quote, candles, pages, observed_at=datetime.now(TPE))
        if pages and pages[-1]["data"]:
            result["trades_status"] = "HOLD_PAGE_CAP_NO_TERMINAL_EMPTY_PAGE"
            result["vwap_status"] = "HOLD"
        result["quote_raw"] = quote
        return result
    except Exception as exc:
        result["collection_error_type"] = type(exc).__name__
        result["five_minute_status"] = "HOLD_PROVIDER_OR_TRANSPORT"
        result["trades_status"] = "HOLD_PROVIDER_OR_TRANSPORT"
        return result



def render_mobile_source_audit(data: dict) -> str:
    """Same-run mobile readback. Research arithmetic is NOT verified trading VWAP."""
    def value(key, default="待確認"):
        item = data.get(key)
        return str(item) if item is not None else default

    status = value("five_minute_status")
    trade_status = value("trades_status")
    volume_status = value("volume_status")
    vwap_status = value("vwap_status")
    count = data.get("returned_bar_count")
    completed = data.get("completed_bar_count")
    excluded = data.get("excluded_incomplete_bar_count")
    # Do not imply completed-only volume equals the current full-session quote.
    lines = [
        "🟡 研究資料觀察｜禁止依此報告新進場",
        f"# Sky 5m驗證 {value('symbol')}",
        f"資料觀察時間：{value('observed_at_tpe')}（Asia/Taipei）",
        f"最後實際成交時間：{value('last_trade_tpe')}",
        f"最後成交觀察價：{value('last_trade_price')} 元（非即時下單價格）",
        "",
        "| 項目 | 本次結果 |",
        "| --- | --- |",
        f"| 五分鐘 K 棒 | {status} |",
        f"| 當次 K 棒總數 | {count if count is not None else '待確認'} |",
        f"| 已完成 K 棒 | {completed if completed is not None else '待確認'} |",
        f"| 排除未完成 K 棒 | {excluded if excluded is not None else '待確認'} |",
        f"| 已完成 K 棒成交量（原始單位） | {value('completed_bar_volume_raw_sum')} |",
        f"| 最後完成棒起始時間 | {value('last_completed_bar_start')} |",
        f"| 逐筆成交分頁 | {trade_status} |",
        f"| 分頁數／結束空頁 | {value('trades_page_count')}／{value('trades_terminal_empty_page')} |",
        f"| 逐筆成交總量（原始單位） | {value('trades_sum_raw_size')} |",
        f"| Quote 成交總量（原始單位） | {value('quote_volume_raw')} |",
        f"| 同源成交量對帳 | {volume_status} |",
        f"| 逐筆成交加權均價（研究級） | {value('trades_weighted_mean_research')} 元 |",
        f"| 正式 VWAP 認證 | {'PASS' if data.get('independent_vwap_certified') is True else 'HOLD'} |",
        f"| VWAP 資料原因 | {vwap_status} |",
        f"| TWSE 外部成交量對帳 | HOLD（本次未取得可比對的同截點官方數據） |",
        f"| 現在動作 | 觀察 |",
        "",
        "研究級同一 Fugle 來源的 K 棒、逐筆成交、Quote 算術核對，不等於 TWSE 獨立校準或原子 PIT 證據。",
        "未完成 K 棒不得進入交易訊號；獨立 VWAP、成本後 RR 與正式風控尚未通過。",
        "自動下單：停用；Production：未核准。",
    ]
    if data.get("collection_error_type"):
        lines.append("採集失敗類型：" + value("collection_error_type"))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--out-dir", default="output/single_stock")
    args = parser.parse_args()
    result = collect(args.symbol)
    path = Path(args.out_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / (args.symbol + "-5m-source.json")).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    (path / (args.symbol + "-5m-source.md")).write_text(
        render_mobile_source_audit(result), encoding="utf-8")
    print(json.dumps({key: result.get(key) for key in
                      ("symbol", "five_minute_status", "trades_status",
                       "volume_status", "vwap_status", "collection_error_type")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
