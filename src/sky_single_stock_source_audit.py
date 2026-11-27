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
from .sky_mobile_table import evidence_scores, direction_label

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
    # Descriptive research observations only; no model score, entry signal or
    # trading VWAP certification is inferred from these arithmetic summaries.
    mean = _number(data.get("trades_weighted_mean_research"))
    last = _number(data.get("last_trade_price"))
    mean_label = f"{mean:.6f} 元（研究觀察）" if mean is not None and mean > 0 else "待確認"
    distance_label = (
        f"{(last / mean - 1) * 100:+.2f}%（歷史觀察，非即時價差）"
        if last is not None and last > 0 and mean is not None and mean > 0
        else "待確認"
    )
    recent_bar_label = "待確認"
    rows = data.get("five_minute_raw")
    n = data.get("completed_bar_count")
    if (data.get("five_minute_status") == "PASS_COMPLETED_BARS_OBSERVED"
            and isinstance(rows, list) and type(n) is int and 2 <= n <= len(rows)):
        previous = _number(rows[n - 2].get("close")) if isinstance(rows[n - 2], dict) else None
        current = _number(rows[n - 1].get("close")) if isinstance(rows[n - 1], dict) else None
        if previous is not None and previous > 0 and current is not None and current > 0:
            change = (current / previous - 1) * 100
            sign = "上升" if change > 0 else "下降" if change < 0 else "持平"
            recent_bar_label = f"{sign} {change:+.2f}%（相鄰兩根已完成棒收盤價）"
    research_data_ready = (
        data.get("five_minute_status") == "PASS_COMPLETED_BARS_OBSERVED"
        and data.get("trades_status") == "PASS_PAGED_RESEARCH_ARITHMETIC_ONLY"
        and data.get("volume_status") == "RECONCILED_SAME_SNAPSHOT_NOT_CROSS_SOURCE_CERTIFIED"
        and mean is not None and mean > 0
    )
    # Do not imply completed-only volume equals the current full-session quote.
    lines = [
        "🟡 研究資料觀察｜禁止依此報告新進場",
        f"# Sky 5m驗證 {value('symbol')}",
        f"資料觀察時間：{value('observed_at_tpe')}（Asia/Taipei）",
        f"最後實際成交時間：{value('last_trade_tpe')}",
        f"最後成交觀察價：{value('last_trade_price')} 元（非即時下單價格）",
        "",
        f"研究數據：{'可供觀察' if research_data_ready else '資料不足，待確認'}；交易訊號：未認證。",
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
        f"| 逐筆成交加權均價（研究級） | {mean_label} |",
        f"| 最後成交價相對研究均價 | {distance_label} |",
        f"| 最近已完成 5m 收盤變動 | {recent_bar_label} |",
        f"| 正式 VWAP 認證 | {'PASS' if data.get('independent_vwap_certified') is True else 'HOLD'} |",
        f"| VWAP 資料原因 | {vwap_status} |",
        f"| TWSE 外部成交量對帳 | HOLD（本次未取得可比對的同截點官方數據） |",
        f"| 現在動作 | 觀察 |",
        "",
        "以上是已取得來源的描述性分析，不是多空勝率、進場點、正式交易建議。",
        "研究級同一 Fugle 來源的 K 棒、逐筆成交、Quote 算術核對，不等於 TWSE 獨立校準或原子 PIT 證據。",
        "未完成 K 棒不得進入交易訊號；獨立 VWAP、成本後 RR 與正式風控尚未通過。",
        "自動下單：停用；Production：未核准。",
    ]
    if data.get("collection_error_type"):
        lines.append("採集失敗類型：" + value("collection_error_type"))
    return "\n".join(lines) + "\n"



def analyze_observation_score(audit: dict) -> dict:
    """Derive the existing quote-only *research* score from this same-run quote.

    Never refetch Fugle or turn quote-refresh time into last execution time.
    """
    outcome = {"status": "RESEARCH_ONLY", "scores": None,
               "score_status": "INSUFFICIENT_VERIFIED_QUOTE",
               "score_direction": None, "execution_authorized": False,
               "live_order_enabled": False, "entry_trigger": None,
               "max_entry": None, "stop": None, "targets": None}
    if not isinstance(audit, dict):
        return outcome
    quote = audit.get("quote_raw")
    if not isinstance(quote, dict):
        return outcome
    try:
        observed = datetime.fromisoformat(audit["observed_at_tpe"])
        executed = datetime.fromisoformat(audit["last_trade_tpe"])
        if (observed.tzinfo is None or executed.tzinfo is None
                or quote.get("date") != observed.astimezone(TPE).date().isoformat()
                or executed.astimezone(TPE).date() != observed.astimezone(TPE).date()
                or not -30 <= (observed - executed).total_seconds() <= 120
                or audit.get("quote_status") != "PASS_ACTUAL_LAST_TRADE_REFERENCE"):
            return outcome
        price = _number(audit.get("last_trade_price"))
        op = _number(quote.get("openPrice"))
        high = _number(quote.get("highPrice"))
        low = _number(quote.get("lowPrice"))
        chg = quote.get("changePercent")
        if (None in (price, op, high, low) or min(price, op, high, low) <= 0
                or not low <= price <= high or not low <= op <= high
                or isinstance(chg, bool) or not isinstance(chg, (int, float))
                or not math.isfinite(float(chg))):
            return outcome
        bull, bear = evidence_scores({"last": price, "open": op,
                                     "high": high, "low": low,
                                     "change_pct": float(chg)})
        if bull is not None and bear is not None:
            outcome["scores"] = {"bull": bull, "bear": bear}
            outcome["score_status"] = "RESEARCH_ONLY_VERIFIED_INTRADAY_QUOTE"
            outcome["score_direction"] = direction_label(bull, bear, {})
    except (ValueError, TypeError, KeyError, OverflowError):
        pass
    return outcome


def render_unified_stock_research(audit: dict, observation: dict) -> str:
    """One phone report from one collection; never authorizes buying."""
    scores = observation.get("scores")
    scores = scores if isinstance(scores, dict) else {}
    bull, bear = scores.get("bull"), scores.get("bear")
    direction = observation.get("score_direction") or "觀察"
    def score_label(v):
        return str(v) if isinstance(v, int) and not isinstance(v, bool) else "待確認"
    symbol = audit.get("symbol", "待確認")
    header = [
        "🟡 研究觀察｜非正式交易訊號",
        f"# Sky 分析 {symbol}",
        "",
        "| 分析項目 | 結果 |",
        "| --- | --- |",
        f"| 方向 | {direction} |",
        f"| 多方研究評分 | {score_label(bull)} |",
        f"| 空方研究評分 | {score_label(bear)} |",
        "| 買進觸發／最高接受價 | 待確認（未執行交易策略） |",
        "| 停損／失效／成本後 RR | 待確認（非交易建議） |",
        "| 現在動作 | 觀察 |",
        "",
        "研究評分不是勝率；來源為同次 Fugle 真實成交時間與日內 OHLC。",
        "若最後成交超過 120 秒、來源失效或 OHLC 不完整，評分保持待確認。",
        "",
        "---",
        "",
    ]
    detail = render_mobile_source_audit(audit).split("\n")
    # Suppress the second title/heading; detail retains all explicit HOLDs.
    if detail and detail[0].startswith("🟡"):
        detail = detail[1:]
    if detail and detail[0].startswith("# Sky 5m驗證"):
        detail = detail[1:]
    return "\n".join(header + detail).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--unified", action="store_true", help="Same-run unified research report")
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
    # Normal Sky 分析: same request budget, one unified JSON + phone Markdown.
    if args.unified:
        observation = analyze_observation_score(result)
        (path / (args.symbol + ".json")).write_text(
            json.dumps({"schema": "SKY_UNIFIED_SINGLE_STOCK_RESEARCH_V1",
                        "symbol": args.symbol, "observation": observation,
                        "source_audit": result, "execution_authorized": False},
                       ensure_ascii=False, indent=2, allow_nan=False) + "\\n",
            encoding="utf-8")
        (path / (args.symbol + ".md")).write_text(
            render_unified_stock_research(result, observation), encoding="utf-8")
    print(json.dumps({key: result.get(key) for key in
                      ("symbol", "five_minute_status", "trades_status",
                       "volume_status", "vwap_status", "collection_error_type")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
