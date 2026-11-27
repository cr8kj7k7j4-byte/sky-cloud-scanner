"""Fail-closed single-stock Fugle API realtime evidence collector.

Read-only data collection. Does NOT produce trade triggers, scores, orders or risk sizing.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import fugle
from .sky_mobile_table import evidence_scores, direction_label

TPE = timezone(timedelta(hours=8))


def timestamp_tpe(value):
    """Accept Fugle epoch microseconds/milliseconds/seconds; return ISO TPE."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
        if number > 1e14:
            number /= 1_000_000
        elif number > 1e11:
            number /= 1_000
        return datetime.fromtimestamp(number, TPE).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def collect(symbol: str, now=None) -> dict:
    now = now or datetime.now(TPE)
    if not (symbol.isdigit() and 4 <= len(symbol) <= 6):
        return {"status": "INVALID_SYMBOL", "symbol": symbol, "action": "禁止交易"}
    result = {
        "symbol": symbol, "source": "Fugle MarketData API /intraday/quote",
        "requested_at_tpe": now.isoformat(), "action": "等待",
        "execution_authorized": False, "live_order_enabled": False,
        "scores": None, "score_status": "INSUFFICIENT_VERIFIED_OHLC",
        "score_version": "SKY_OBSERVATIONAL_EVIDENCE_V1",
        "entry_trigger": None, "max_entry": None,
        "stop": None, "targets": None, "net_rr": None,
        "field_missing_reasons": {
            "多方評分": "本行情收集器不執行正式多方模型，缺多週期與完整策略證據",
            "空方評分": "本行情收集器不執行獨立空方模型，缺獨立空方訊號",
            "買進觸發": "缺同次已驗證的策略觸發與突破品質，不可由報價反推",
            "最高接受價": "缺合格觸發、追高否決與成本後RR檢查",
            "停損／失效": "缺合格策略結構停損與實際失效條件",
            "目標價": "缺同次已核准的策略目標一／二，不以價格乘數捏造",
            "成本後RR": "缺合格進場、停損、目標與費稅／價差／滑價證據",
        },
    }
    try:
        quote = fugle.get_quote(symbol)
        ticker = fugle.get_ticker(symbol)
        if not isinstance(quote, dict) or not isinstance(ticker, dict):
            raise ValueError("Invalid Fugle response payload")
        trade = quote.get("lastTrade")
        trade = trade if isinstance(trade, dict) else {}
        last_trade_price = trade.get("price")
        last_price = last_trade_price if last_trade_price is not None else quote.get("lastPrice")
        # A quote refresh/closeTime is not a last executed-trade timestamp.
        last_time = timestamp_tpe(trade.get("time"))
        updated_time = timestamp_tpe(quote.get("lastUpdated"))
        result.update({
            "quote_date": quote.get("date"), "last_price": last_price,
            "last_trade_price": last_trade_price,
            "observed_price": last_price, "observed_at_tpe": now.isoformat(),
            "observation_requires_last_trade_time": False,
            "executed_trade_verified": False,
            "last_trade_tpe": last_time, "last_updated_tpe": updated_time,
            "high": quote.get("highPrice"), "low": quote.get("lowPrice"),
            "open": quote.get("openPrice"), "average_price": quote.get("avgPrice"),
            "volume": (quote.get("total") or {}).get("tradeVolume"),
            "best_bid": ((quote.get("bids") or [{}])[0]).get("price"),
            "best_ask": ((quote.get("asks") or [{}])[0]).get("price"),
            "day_trade_eligible": ticker.get("canDayTrade"),
            "is_disposition": ticker.get("isDisposition"),
            "quote_market": quote.get("market"),
        })
        if (isinstance(last_price, bool) or not isinstance(last_price, (float, int))
                or last_price <= 0):
            result["status"] = "INVALID_OR_MISSING_PRICE"
        elif quote.get("date") != now.date().isoformat():
            result["status"] = "STALE_TRADING_DATE"
        elif not last_time:
            # Preserve an observed price while withholding verified-live status.
            result["status"] = "UNVERIFIED_EXECUTION_TIME"
        else:
            seen = datetime.fromisoformat(last_time)
            quote_date = quote.get("date")
            age = (now - seen).total_seconds()
            result["quote_age_seconds"] = round(age, 1)
            # Position-review observation is separate from new-entry eligibility.
            # It requires the actual lastTrade.price; lastPrice fallback is NOT evidence.
            result["position_trade_observed"] = bool(
                not isinstance(last_trade_price, bool)
                and isinstance(last_trade_price, (int, float))
                and math.isfinite(float(last_trade_price))
                and last_trade_price > 0
                and quote_date == now.date().isoformat()
                and seen.date() == now.date()
                and -30 <= age <= 120
            )
            if quote_date != now.date().isoformat() or seen.date() != now.date():
                result["status"] = "STALE_TRADING_DATE"
            elif age < -30:
                result["status"] = "FUTURE_QUOTE_TIMESTAMP"
            elif age > 120:
                result["status"] = "STALE_QUOTE"
            elif ticker.get("canDayTrade") is not True:
                result["status"] = "DAY_TRADE_NOT_ELIGIBLE"
            elif ticker.get("isDisposition") is True:
                result["status"] = "DISPOSITION_NO_NEW_ENTRY"
            elif last_price >= float(os.environ.get("MAX_PRICE", "100")):
                result["status"] = "PRICE_CAP_EXCEEDED"
            else:
                result["status"] = "REALTIME_QUOTE_VERIFIED"
                result["executed_trade_verified"] = True
        # Display-only observation scores are independent of broker account,
        # daytrade eligibility and P0-R. They never authorize orders or entries.
        # Require actual executed price/time, same-session fresh data and valid
        # same-day Fugle OHLC; quote lastPrice/refresh time are not substitutes.
        def positive(value):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            number = float(value)
            return number if math.isfinite(number) and number > 0 else None

        executed = positive(last_trade_price)
        op = positive(quote.get("openPrice"))
        hi = positive(quote.get("highPrice"))
        lo = positive(quote.get("lowPrice"))
        chg = quote.get("changePercent")
        age = result.get("quote_age_seconds")
        trade_fresh = (last_time is not None and isinstance(age, (int, float))
                       and -30 <= age <= 120 and quote.get("date") == now.date().isoformat()
                       and datetime.fromisoformat(last_time).date() == now.date())
        if (trade_fresh and None not in (executed, op, hi, lo)
                and lo <= executed <= hi and lo <= op <= hi
                and isinstance(chg, (int, float)) and not isinstance(chg, bool)
                and math.isfinite(float(chg))):
            bull, bear = evidence_scores({
                "last": executed, "open": op, "high": hi, "low": lo,
                "change_pct": float(chg),
            })
            if bull is not None and bear is not None:
                result["scores"] = {"bull": bull, "bear": bear}
                result["score_direction"] = direction_label(bull, bear, {})
                result["score_status"] = "RESEARCH_ONLY_VERIFIED_INTRADAY_QUOTE"
                result["field_missing_reasons"].pop("多方評分", None)
                result["field_missing_reasons"].pop("空方評分", None)
        return result
    except Exception as exc:
        result.update({"status": "QUOTE_FETCH_FAILED", "error_type": type(exc).__name__})
        # Only this allowlisted, credential-free failure code is safe to expose.
        # Never serialize arbitrary provider exceptions, URLs, tokens or payloads.
        if isinstance(exc, RuntimeError) and str(exc) == "DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED":
            result["block_reason"] = "DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED"
        return result



def render_mobile_observation(payload: dict) -> str:
    """Present the same collected payload; never trigger another Fugle call.

    Research scores and prices are displayed separately from entry authorization.
    A stale last-trade price is labeled as historical observation, never live.
    """
    def clean(value):
        if value is None or value == "":
            return "待確認"
        return str(value).replace("|", "／").replace("\n", " ").replace("\r", " ")

    def price(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return "待確認"
        n = float(value)
        return f"{n:.2f}" if math.isfinite(n) and n > 0 else "待確認"

    status = payload.get("status") or "MISSING_STATUS"
    scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    scored = payload.get("score_status") == "RESEARCH_ONLY_VERIFIED_INTRADAY_QUOTE"
    bull = scores.get("bull") if scored else None
    bear = scores.get("bear") if scored else None
    last_trade = payload.get("last_trade_tpe")
    observed_price = price(payload.get("last_trade_price"))
    # Having a historical executed price does not establish freshness.
    age = payload.get("quote_age_seconds")
    fresh = (
        isinstance(age, (int, float)) and not isinstance(age, bool)
        and -30 <= age <= 120
        and scored and last_trade is not None
    )
    current_price = observed_price if fresh else "待確認（非新鮮成交）"
    line = [
        "🔴 禁止新進場｜研究觀察級，非正式交易訊號",
        "",
        f"# Sky 分析 {clean(payload.get('symbol'))}",
        "",
        "| 欄位 | 結果 |",
        "| --- | --- |",
        f"| 股票 | {clean(payload.get('symbol'))} |",
        f"| 現價 | {current_price} |",
        f"| 方向 | {clean(payload.get('score_direction')) if scored else '觀察'} |",
        f"| 多方評分 | {clean(bull) if bull is not None else '待確認'} |",
        f"| 空方評分 | {clean(bear) if bear is not None else '待確認'} |",
        "| 買進觸發 | 待確認（缺合格策略計畫） |",
        "| 最高接受價 | 待確認（缺合格策略計畫） |",
        "| 停損／失效 | 待確認（缺合格策略計畫） |",
        "| 分類 | X（未通過正式新進場驗證） |",
        "| 現在動作 | 等待 |",
        "",
        f"Fugle 來源：{clean(payload.get('source'))}",
        f"資料交易日：{clean(payload.get('quote_date'))}（Asia/Taipei）",
        f"實際最後成交時間：{clean(last_trade)}",
        f"掃描時間：{clean(payload.get('requested_at_tpe'))}",
        f"最後實際成交觀察價：{observed_price}（不代表目前可成交價格）",
        f"資料狀態：{clean(status)}；評分狀態：{clean(payload.get('score_status'))}",
        f"研究演算法：{clean(payload.get('score_version'))}；分數不是勝率。",
        "未完成五分鐘 K 棒、多週期、成本後 RR 與 P0-R 驗證；不得由觀察分數反推買進或加碼價。",
        "自動下單：停用；正式進場資格：未通過。",
    ]
    return "\n".join(line) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    payload = collect(args.symbol)
    path = Path(args.output or f"output/single_stock/{args.symbol}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # Same-run mobile report goes into the existing Artifact directory.
    path.with_suffix(".md").write_text(render_mobile_observation(payload), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    # Collecting a valid unverified observation succeeds as research ingestion.
    # Its payload still explicitly denies executed-trade verification and orders.
    # Research-only valid scores are successful observations even when daytrade
    # eligibility / price cap denies trading. Never weaken data freshness gates.
    observation_scored = (
        payload.get("score_status") == "RESEARCH_ONLY_VERIFIED_INTRADAY_QUOTE"
        and isinstance(payload.get("scores"), dict)
        and payload["scores"].get("bull") is not None
        and payload["scores"].get("bear") is not None
    )
    # The owner requests source-labeled analysis, not executable trades.
    # A truly executed but STALE quote may still produce a research reference
    # Artifact. Never call it live, never score it, and never accept a missing,
    # future, wrong-session or invalid executed price/time as evidence.
    stale_reference = False
    if payload.get("status") == "STALE_QUOTE":
        try:
            trade_price = payload.get("last_trade_price")
            stamp = datetime.fromisoformat(payload["last_trade_tpe"])
            requested = datetime.fromisoformat(payload["requested_at_tpe"])
            age = payload.get("quote_age_seconds")
            stale_reference = (
                isinstance(trade_price, (int, float)) and not isinstance(trade_price, bool)
                and math.isfinite(float(trade_price)) and trade_price > 0
                and stamp.tzinfo is not None and requested.tzinfo is not None
                and stamp.date() == requested.date()
                and payload.get("quote_date") == requested.date().isoformat()
                and isinstance(age, (int, float)) and not isinstance(age, bool)
                and math.isfinite(float(age)) and age > 120
                and abs((requested - stamp).total_seconds() - age) < 2
            )
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
    if not observation_scored and not stale_reference and payload["status"] not in (
        "REALTIME_QUOTE_VERIFIED", "UNVERIFIED_EXECUTION_TIME"
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
