"""Read-only on-demand proof of ticker and 5m-candle provenance.

At most one already quote-verified candidate per market. This does NOT create
a v1.4 signal or infer 5m breakout profitability. Never sends orders.
"""
from __future__ import annotations
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

from src.fugle import get_ticker, get_candles
from src.feature_engine import build_features

TPE = ZoneInfo("Asia/Taipei")


def selected(stage2):
    if stage2.get("schema") != "SKY_STAGE2_BOUNDED_QUOTE_EVIDENCE_V1":
        raise ValueError("BAD_STAGE2_SCHEMA")
    picked=[]
    for market in ("TWSE","TPEx"):
        for x in stage2.get("results", []):
            if (x.get("exchange")==market and x.get("executed_trade_verified") is True
                    and x.get("microstructure", {}).get("turnover_gate_pass") is True
                    and x.get("microstructure", {}).get("l1_spread_gate_pass") is True):
                picked.append(x)
                break
    return picked


def run(stage2, *, ticker_fn=get_ticker, candle_fn=get_candles, sleep_fn=time.sleep, now=None):
    now=now or datetime.now(TPE)
    selected_rows=selected(stage2)
    output=[]
    attempts=0
    hit429=False
    for row in selected_rows:
        result={"symbol":row["symbol"],"exchange":row["exchange"],
                "production_eligible":False,"action":"等待",
                "v14_full_rule_validated":False,"breakout_quality_validated":False,
                "complete_execution_cost_rr":False}
        try:
            attempts+=1
            ticker=ticker_fn(row["symbol"])
            sleep_fn(1.0)
            attempts+=1
            candles=candle_fn(row["symbol"],timeframe="5")
            if isinstance(ticker,dict) and isinstance(ticker.get("data"),dict):
                ticker=ticker["data"]
            if not isinstance(ticker,dict) or not isinstance(candles,dict):
                result["status"]="INVALID_PROVIDER_PAYLOAD"
            else:
                day=now.date().isoformat()
                tdate=ticker.get("date")
                cdate=candles.get("date")
                actual_tf=str(candles.get("timeframe") or "")
                bars=candles.get("data")
                # Research PIT guard: conservatively treat the timestamp as a bar
                # START until provider semantics are formally certified. Never use
                # any bar that could still be forming at the scan observation time.
                valid=[]
                rejected_future_bars=0
                excluded_incomplete_bars=0
                invalid_bar_sequence=False
                prior_stamp=None
                if isinstance(bars,list):
                    for b in bars:
                        if not isinstance(b,dict):
                            invalid_bar_sequence=True
                            continue
                        try:
                            stamp=datetime.fromisoformat(str(b["date"]).replace("Z","+00:00"))
                            if stamp.utcoffset() is None:
                                invalid_bar_sequence=True
                                continue
                            stamp=stamp.astimezone(TPE)
                            if prior_stamp is not None and stamp<=prior_stamp:
                                invalid_bar_sequence=True  # duplicate or out of order
                            prior_stamp=stamp
                            if stamp.date()!=now.date():
                                invalid_bar_sequence=True
                                continue
                            if stamp>now:
                                rejected_future_bars+=1
                                continue
                            if stamp+timedelta(minutes=5)>now:
                                excluded_incomplete_bars+=1
                                continue
                            if b.get("close") is None or b.get("volume") is None:
                                invalid_bar_sequence=True
                                continue
                            valid.append(b)
                        except (KeyError, ValueError, TypeError, OverflowError):
                            invalid_bar_sequence=True
                            continue
                boardlot=ticker.get("boardLot")
                eligible=ticker.get("canDayTrade") is True and ticker.get("canBuyDayTrade") is True
                quote_price=row.get("verified_trade_price")
                limit=ticker.get("limitUpPrice")
                is_limit=bool(quote_price is not None and limit is not None and float(quote_price)>=float(limit))
                snapshot={
                    "last":quote_price,"avg_price":row.get("microstructure",{}).get("average_price")
                }
                # Do not expose potentially contaminated model features from
                # invalid bar order, future bars, or mismatched source dates.
                preview_safe = (len(valid)>=2 and not invalid_bar_sequence
                                and rejected_future_bars==0 and actual_tf=="5"
                                and tdate==day and cdate==day)
                features=build_features(snapshot,valid).to_dict() if preview_safe else None
                result.update({
                    "ticker_date":tdate,"candles_date":cdate,
                    "board_lot_shares":boardlot,
                    "trading_currency":ticker.get("tradingCurrency"),
                    "can_day_trade":ticker.get("canDayTrade"),
                    "can_buy_day_trade":ticker.get("canBuyDayTrade"),
                    "security_status":ticker.get("securityStatus"),
                    "is_disposition":ticker.get("isDisposition"),
                    "is_attention":ticker.get("isAttention"),
                    "is_specific_abnormal":ticker.get("isSpecificAbnormally"),
                    "limit_up":limit,"is_limit_up":is_limit,
                    "candles_timeframe":actual_tf,
                    "valid_today_five_min_bars":len(valid),
                    "rejected_future_five_min_bars":rejected_future_bars,
                    "excluded_unfinished_five_min_bars":excluded_incomplete_bars,
                    "bar_sequence_valid":not invalid_bar_sequence,
                    "last_feature_bar_time_tpe":valid[-1]["date"] if valid else None,
                    "bar_timestamp_semantics_certified":False,
                    "feature_preview":features,
                    "avg_price_is_certified_vwap":False,
                    "official_bar_volume_unit":"整股張數（Fugle 官方 Intraday Candles 文件）",
                })
                ready=(tdate==day and cdate==day and actual_tf=="5" and len(valid)>=6
                       and not invalid_bar_sequence and rejected_future_bars==0
                       and eligible and not is_limit and ticker.get("securityStatus")=="NORMAL"
                       and ticker.get("isDisposition") is False
                       and ticker.get("isAttention") is False
                       and ticker.get("isSpecificAbnormally") is False
                       and boardlot is not None and float(boardlot)>0)
                result["status"]="CANDLE_TICKER_RESEARCH_READY_NOT_TRADE" if ready else "INCOMPLETE_TICKER_OR_5M_EVIDENCE"
        except requests.HTTPError as exc:
            status=exc.response.status_code if exc.response is not None else None
            result["status"]="RATE_LIMITED" if status==429 else "HTTP_ERROR"
            result["http_status"]=status
            hit429 = status==429
        except (PermissionError,ValueError,TypeError,requests.RequestException) as exc:
            result["status"]="SOURCE_ERROR"
            result["error_type"]=type(exc).__name__
        output.append(result)
        if hit429:
            break
        sleep_fn(1.0)
    return {
        "schema":"SKY_V14_TICKER_5M_RESEARCH_PROVENANCE_V1",
        "time_tpe":now.isoformat(),
        "attempted_api_requests":attempts,
        "rate_limited":hit429,
        "samples":output,
        "official_v14_entry_eligible":False,
        "whole_market_certified":False,
        "execution_cost_rr_complete":False,
        "production_eligible":False,
        "automatic_order":False,
        "trade_decision":"🔴 禁止新進場、未驗證通過",
    }
