"""Read-only on-demand proof of ticker and 5m-candle provenance.

At most one already quote-verified candidate per market. This does NOT create
a v1.4 signal or infer 5m breakout profitability. Never sends orders.
"""
from __future__ import annotations
import time
import math
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

from src.fugle import get_ticker, get_candles
from src.feature_engine import build_features
from src.sky_kbar_evidence_policy import classify as classify_kbar, NO_BARS as KBAR_NO_BARS, SPARSE as KBAR_SPARSE

TPE = ZoneInfo("Asia/Taipei")


def positive_finite_number(value):
    """Only genuine positive finite provider numbers can satisfy ticker gates."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None



def research_bar_average_weighted_observation(bars, *, now):
    """Preserve raw average but refuse to infer interval VWAP.

    Fugle Historical Candles defines minute-bar average as cumulative
    average price from market open. Intraday Candles labels its field only
    as average price and does not establish interval-specific VWAP semantics.
    Therefore average_i * volume_i is not a valid independent VWAP
    reconstruction without an explicit provider contract. This diagnostic
    intentionally never computes a weighted average.
    """
    valid_now = isinstance(now, datetime) and now.utcoffset() is not None
    completed = 0
    preserved_average_count = 0
    if isinstance(bars, list) and valid_now:
        prior = None
        for bar in bars:
            if not isinstance(bar, dict):
                continue
            try:
                stamp = datetime.fromisoformat(str(bar["date"]).replace("Z", "+00:00"))
                if stamp.utcoffset() is None:
                    continue
                stamp = stamp.astimezone(TPE)
            except (KeyError, ValueError, TypeError, OverflowError):
                continue
            if (stamp.date() != now.astimezone(TPE).date() or stamp.minute % 5
                    or stamp.second or stamp.microsecond
                    or (prior is not None and stamp <= prior)):
                prior = stamp
                continue
            prior = stamp
            if stamp + timedelta(minutes=5) > now.astimezone(TPE):
                continue
            completed += 1
            if positive_finite_number(bar.get("average")) is not None:
                preserved_average_count += 1
    return {
        "status": "INTRADAY_AVERAGE_SEMANTICS_UNVERIFIED_NO_VWAP",
        "source": "FUGLE_INTRADAY_CANDLES_AVERAGE_FIELD",
        "average_semantics": "NOT_DOCUMENTED_AS_INTERVAL_VWAP",
        "historical_minute_average_semantics": "CUMULATIVE_FROM_MARKET_OPEN",
        "weighted_average_observation": None,
        "completed_bar_count": completed,
        "completed_bars_with_finite_average": preserved_average_count,
        "point_in_time_certified": False,
        "independent_tick_vwap_certified": False,
        "production_eligible": False,
    }

def selected(stage2):
    if stage2.get("schema") != "SKY_STAGE2_BOUNDED_QUOTE_EVIDENCE_V1":
        raise ValueError("BAD_STAGE2_SCHEMA")
    picked=[]
    for market in ("TWSE","TPEx"):
        for x in stage2.get("results", []):
            if not isinstance(x, dict):
                continue
            micro = x.get("microstructure")
            symbol = x.get("symbol")
            if (x.get("exchange")==market
                    and isinstance(symbol, str) and symbol.isascii() and symbol.isdigit()
                    and x.get("executed_trade_verified") is True
                    and isinstance(micro, dict)
                    and micro.get("turnover_gate_pass") is True
                    and micro.get("l1_spread_gate_pass") is True):
                picked.append(x)
                break
    return picked


def run(stage2, *, ticker_fn=get_ticker, candle_fn=get_candles, sleep_fn=time.sleep, now=None, evidence_candidates=None):
    now=now or datetime.now(TPE)
    # Provider candle times are normalized to Asia/Taipei below. Normalize
    # observation time to the same exchange-local calendar *before* comparing
    # provider day fields or unfinished 5m bars. Naive clocks fail closed.
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("OBSERVATION_TIME_REQUIRES_AWARE_DATETIME")
    now=now.astimezone(TPE)
    if evidence_candidates is None:
        selected_rows=selected(stage2)
    else:
        # Isolated evidence-only path: never misrepresent these as Stage2
        # quote-verified candidates, nor use them to approve model features.
        if (not isinstance(evidence_candidates, list) or len(evidence_candidates)!=2
                or {x.get("exchange") for x in evidence_candidates if isinstance(x,dict)}!={"TWSE","TPEx"}
                or any(not isinstance(x, dict)
                       or not isinstance(x.get("symbol"), str)
                       or not x["symbol"].isdigit()
                       for x in evidence_candidates)):
            raise ValueError("BAD_EVIDENCE_SAMPLE_SET")
        selected_rows=evidence_candidates
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
            ticker_received_at_tpe=datetime.now(TPE).isoformat()
            sleep_fn(1.0)
            attempts+=1
            candles=candle_fn(row["symbol"],timeframe="5")
            candles_received_at_tpe=datetime.now(TPE).isoformat()
            result["ticker_received_at_tpe"]=ticker_received_at_tpe
            result["candles_received_at_tpe"]=candles_received_at_tpe
            result["observation_time_tpe"]=now.isoformat()
            if isinstance(ticker,dict) and isinstance(ticker.get("data"),dict):
                ticker=ticker["data"]
            if not isinstance(ticker,dict) or not isinstance(candles,dict):
                result["status"]="INVALID_PROVIDER_PAYLOAD"
            else:
                day=now.date().isoformat()
                tdate=ticker.get("date")
                cdate=candles.get("date")
                actual_tf=str(candles.get("timeframe") or "")
                # Both official Fugle endpoints return symbol and exchange.
                # A cross-stock or cross-exchange response must never be
                # used for this candidate's model feature preview.
                source_identity_matches=(
                    ticker.get("symbol")==row["symbol"]
                    and candles.get("symbol")==row["symbol"]
                    and ticker.get("exchange")==row["exchange"]
                    and candles.get("exchange")==row["exchange"]
                )
                bars=candles.get("data")
                # Preserve a bounded, credential-free raw provider receipt for
                # later same-SHA Artifact inspection; do not infer its semantics.
                result["raw_five_min_candles"]={
                    "source_endpoint":"FUGLE_INTRADAY_CANDLES",
                    "source_request_timeframe":"5",
                    "symbol":candles.get("symbol"),
                    "exchange":candles.get("exchange"),
                    # Required to validate provider unit by security type.
                    # Missing source type is never silently treated as a board lot.
                    "type":candles.get("type"),
                    "market":candles.get("market"),
                    "date":candles.get("date"),
                    "timeframe":candles.get("timeframe"),
                    "data":[{key:bar.get(key) for key in ("date","open","high","low","close","volume","average")}
                            for bar in bars if isinstance(bar,dict)][:100]
                            if isinstance(bars,list) else None,
                }
                # Research PIT guard: conservatively treat the timestamp as a bar
                # START until provider semantics are formally certified. Never use
                # any bar that could still be forming at the scan observation time.
                valid=[]
                last_accepted_stamp=None
                rejected_future_bars=0
                excluded_incomplete_bars=0
                invalid_bar_sequence=False
                missing_five_min_slots=0
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
                            # A 5-minute candle must start on a local 5-minute
                            # grid. Reject malformed minute/second offsets
                            # rather than treating them as certified 5m bars.
                            if stamp.minute % 5 or stamp.second or stamp.microsecond:
                                invalid_bar_sequence=True
                                continue
                            if prior_stamp is not None:
                                if stamp<=prior_stamp:
                                    invalid_bar_sequence=True  # duplicate or out of order
                                elif stamp-prior_stamp > timedelta(minutes=5):
                                    # Fugle legitimately omits no-trade intervals.
                                    # This is a coverage observation, not corrupt data.
                                    missing_five_min_slots += max(
                                        0, int((stamp-prior_stamp).total_seconds() // 300) - 1)
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
                            close, volume = b.get("close"), b.get("volume")
                            if (isinstance(close, bool) or isinstance(volume, bool)
                                    or not isinstance(close, (int, float))
                                    or not isinstance(volume, (int, float))
                                    or not math.isfinite(close) or not math.isfinite(volume)
                                    or close <= 0 or volume < 0):
                                invalid_bar_sequence=True
                                continue
                            # Some provider receipts include OHLC; never allow
                            # contradictory or non-finite OHLC into features.
                            # Close-only legacy fixtures remain observation-only.
                            ohlc_keys=("open", "high", "low")
                            if any(k in b for k in ohlc_keys):
                                if not all(k in b for k in ohlc_keys):
                                    invalid_bar_sequence=True
                                    continue
                                opening, high, low = (b[k] for k in ohlc_keys)
                                if (any(isinstance(v, bool) or not isinstance(v, (int, float))
                                        or not math.isfinite(v) or v <= 0
                                        for v in (opening, high, low))
                                        or high < max(opening, close)
                                        or low > min(opening, close)
                                        or low > high):
                                    invalid_bar_sequence=True
                                    continue
                            valid.append(b)
                            last_accepted_stamp=stamp
                        except (KeyError, ValueError, TypeError, OverflowError):
                            invalid_bar_sequence=True
                            continue
                boardlot=ticker.get("boardLot")
                ticker_type=ticker.get("type")
                candle_type=candles.get("type")
                # Fugle Intraday Candles: regular EQUITY uses board lots,
                # odd-lot/emerging uses shares, and index uses turnover money.
                # Contract matching is separate from actual volume reconciliation.
                equity_lot_contract_matched=(
                    source_identity_matches
                    and ticker_type=="EQUITY" and candle_type=="EQUITY"
                    and row["exchange"] in ("TWSE", "TPEx")
                    and type(boardlot) in (int, float) and boardlot==1000
                )
                eligible=ticker.get("canDayTrade") is True and ticker.get("canBuyDayTrade") is True
                quote_price=row.get("verified_trade_price")
                limit=ticker.get("limitUpPrice")
                verified_price=positive_finite_number(quote_price)
                upper_limit=positive_finite_number(limit)
                # Unknown/malformed limit-up values must never pass the ticker gate.
                is_limit=bool(verified_price is not None and upper_limit is not None
                              and verified_price >= upper_limit)
                micro = row.get("microstructure")
                avg_price = positive_finite_number(
                    micro.get("average_price") if isinstance(micro, dict) else None
                )
                # A malformed provider average must not crash feature preview
                # or be mistaken for a certified VWAP observation.
                # A quote mean is not an independently authenticated tick
                # VWAP. Never label a price-vs-mean ratio as vwap_distance_pct.
                # Preserve the observed quote mean separately for research.
                snapshot={"last":verified_price, "avg_price":None}
                # Do not expose potentially contaminated model features from
                # invalid bar order, future bars, or mismatched source dates.
                preview_safe = (evidence_candidates is None and source_identity_matches and len(valid)>=2 and not invalid_bar_sequence
                                and rejected_future_bars==0 and not missing_five_min_slots and actual_tf=="5"
                                and tdate==day and cdate==day)
                features=build_features(snapshot,valid).to_dict() if preview_safe else None
                kbar_valid = (source_identity_matches and actual_tf=="5" and cdate==day
                              and not invalid_bar_sequence and rejected_future_bars == 0)
                kbar_policy = classify_kbar(
                    source_valid=kbar_valid,
                    observed_bars=len(valid),
                    missing_slots=missing_five_min_slots)
                result.update(kbar_policy)
                result.update({
                    "missing_five_minute_slots_observed": missing_five_min_slots,
                    "bar_coverage_contiguous": missing_five_min_slots == 0,
                    "ticker_date":tdate,"candles_date":cdate,
                    "source_identity_matches":source_identity_matches,
                    "board_lot_shares":boardlot,
                    "ticker_source_type":ticker_type,
                    "candle_source_type":candle_type,
                    "provider_quote_average_unverified":avg_price,
                    "vwap_feature_status":"HOLD_INDEPENDENT_TICK_VWAP_MISSING",
                    "bar_volume_unit_contract_status":(
                        "MATCH_FUGLE_REGULAR_EQUITY_1000_SHARES_PER_LOT"
                        if equity_lot_contract_matched else
                        "HOLD_SOURCE_TYPE_OR_BOARD_LOT_UNVERIFIED"),
                    "bar_volume_share_multiplier":1000 if equity_lot_contract_matched else None,
                    "bar_volume_cross_source_reconciled":False,
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
                    "last_feature_bar_time_tpe":last_accepted_stamp.isoformat() if last_accepted_stamp else None,
                    "bar_timestamp_semantics_certified":False,
                    "feature_preview":features,
                    "bar_average_weighted_observation":(
                        research_bar_average_weighted_observation(bars, now=now)
                        if source_identity_matches and actual_tf=="5" and cdate==day
                           and not invalid_bar_sequence and rejected_future_bars==0
                        else {"status":"INVALID_SOURCE_OR_BAR_SEQUENCE",
                              "point_in_time_certified":False,
                              "independent_tick_vwap_certified":False,
                              "production_eligible":False}),
                    "avg_price_is_certified_vwap":False,
                    "official_bar_volume_unit":(
                        "整股張數（1張=1000股；僅來源類型符合官方契約）"
                        if equity_lot_contract_matched else None),
                })
                ready=(evidence_candidates is None and source_identity_matches and tdate==day and cdate==day
                       and actual_tf=="5" and len(valid)>=6
                       and not missing_five_min_slots
                       and not invalid_bar_sequence and rejected_future_bars==0
                       and eligible and not is_limit and ticker.get("securityStatus")=="NORMAL"
                       and ticker.get("isDisposition") is False
                       and ticker.get("isAttention") is False
                       and ticker.get("isSpecificAbnormally") is False
                       and positive_finite_number(boardlot) is not None
                       and verified_price is not None and upper_limit is not None)
                result["status"]=(
                    KBAR_NO_BARS if kbar_valid and not valid
                    else KBAR_SPARSE if kbar_valid and missing_five_min_slots
                    else "RAW_5M_RESEARCH_SAMPLE_NO_STAGE2" if evidence_candidates is not None
                    else "CANDLE_TICKER_RESEARCH_READY_NOT_TRADE" if ready
                    else "INCOMPLETE_TICKER_OR_5M_EVIDENCE")
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
        "stage2_quote_verified":evidence_candidates is None,
        "head_sha":os.environ.get("GITHUB_SHA"),
        "run_id":os.environ.get("GITHUB_RUN_ID"),
        "data_receipt_kind":"LIVE_ONLY_IF_PROVIDER_CONFIRMED",
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
