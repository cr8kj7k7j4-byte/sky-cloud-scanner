"""Official-source layer.

TWSE universe: TWSE OpenAPI STOCK_DAY_ALL.
TPEx universe: TPEx OpenAPI tpex_mainboard_quotes.
Intraday quotes: TWSE MIS supports both TSE and OTC symbols. For OTC this is an
operational fallback, NOT a TPEx-official intraday source. STRICT_OFFICIAL_MODE
therefore never certifies a complete full-market scan from MIS-OTC alone.
"""
import re, time
from .http_utils import get_json, session

TWSE_UNIVERSE_URL="https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX_UNIVERSE_URL="https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
MIS_URL="https://mis.twse.com.tw/stock/api/getStockInfo.jsp"

COMMON=re.compile(r"^[1-9][0-9]{3}$")

def _f(v):
    if v in (None,"","-","--","---"): return None
    try: return float(str(v).replace(",",""))
    except Exception: return None

def _i(v):
    x=_f(v); return int(x) if x is not None else 0

def load_official_universe():
    warnings=[]; out={}
    try:
        data=get_json(TWSE_UNIVERSE_URL)
        for x in data if isinstance(data,list) else []:
            code=str(x.get("Code") or x.get("證券代號") or "").strip()
            if COMMON.match(code):
                out[code]={"symbol":code,"name":x.get("Name") or x.get("證券名稱") or "","exchange":"TWSE","market":"TSE","mis_prefix":"tse","universe_source":"TWSE OpenAPI"}
    except Exception as e: warnings.append(f"TWSE universe failed: {type(e).__name__}: {e}")
    twse_count=sum(1 for x in out.values() if x["exchange"]=="TWSE")
    try:
        data=get_json(TPEX_UNIVERSE_URL)
        for x in data if isinstance(data,list) else []:
            code=str(x.get("SecuritiesCompanyCode") or x.get("Code") or "").strip()
            if COMMON.match(code):
                out[code]={"symbol":code,"name":x.get("CompanyName") or x.get("Name") or "","exchange":"TPEx","market":"OTC","mis_prefix":"otc","universe_source":"TPEx OpenAPI"}
    except Exception as e: warnings.append(f"TPEx universe failed: {type(e).__name__}: {e}")
    tpex_count=sum(1 for x in out.values() if x["exchange"]=="TPEx")
    return list(out.values()), {"twse":twse_count,"tpex":tpex_count,"warnings":warnings}

def fetch_mis_quotes(universe, batch_size=55, sleep_s=.18):
    """Fetch TWSE MIS quotes with bounded recovery for truncated multi-symbol responses.

    A successful HTTP 200 does not mean that all requested symbols were returned.
    In particular, large ex_ch batches may silently return only a few entries.
    Re-query only the omitted symbols in small batches, preserving source and
    never fabricating a trade for a symbol without a valid last price.
    """
    s=session()
    s.headers.update({"Referer":"https://mis.twse.com.tw/stock/index.jsp"})
    try: s.get("https://mis.twse.com.tw/stock/index.jsp",timeout=15)
    except Exception: pass

    rows_by_symbol={}
    warnings=[]
    stats={"initial_requested":len(universe),"initial_returned":0,
           "recovery_requested":0,"recovery_returned":0,
           "missing_after_recovery":0,"no_valid_trade":0,"failed_requests":0}

    def request(batch, *, recovery=False):
        if not batch:
            return []
        ex_ch="|".join(f'{x["mis_prefix"]}_{x["symbol"]}.tw' for x in batch)
        # Retry only transient server/rate-limit responses, with a strict
        # two-attempt budget. Never retry authorization denial or bad requests.
        for attempt in range(2):
            try:
                r=s.get(MIS_URL,params={"ex_ch":ex_ch,"json":"1","delay":"0"},timeout=20)
                r.raise_for_status()
                payload=r.json()
                arr=payload.get("msgArray",[])
                if not isinstance(arr,list):
                    raise ValueError("MIS msgArray is not a list")
                requested={x["symbol"] for x in batch}
                found=[q for q in arr if str(q.get("c","")).strip() in requested]
                stats["recovery_returned" if recovery else "initial_returned"]+=len({str(q["c"]).strip() for q in found})
                return found
            except Exception as e:
                status=getattr(getattr(e,"response",None),"status_code",None)
                transient=(status in (429,500,502,503,504))
                if transient and attempt==0:
                    stats["http_retries"]=stats.get("http_retries",0)+1
                    # Keep total network load bounded and respect Retry-After
                    # without permitting an arbitrarily long provider delay.
                    headers=getattr(getattr(e,"response",None),"headers",{}) or {}
                    raw_retry=headers.get("Retry-After")
                    try:
                        retry_after=max(0.0,min(float(raw_retry),2.0))
                    except (TypeError,ValueError):
                        retry_after=0.5
                    time.sleep(max(0.5,retry_after))
                    continue
                stats["failed_requests"]+=1
                if status is not None:
                    key=f"http_{status}"
                    stats[key]=stats.get(key,0)+1
                if sum("batch failed" in w for w in warnings)<5:
                    detail=f"HTTP {status}" if status is not None else type(e).__name__
                    warnings.append(
                        f"MIS {'recovery' if recovery else 'initial'} batch failed: "
                        f"{detail}: {str(e)[:100]}"
                    )
                return []

    def ingest(arr, meta):
        for q in arr:
            code=str(q.get("c","")).strip()
            m=meta.get(code)
            if not m:
                continue
            last=_f(q.get("z"))
            prev=_f(q.get("y"))
            if last is None or prev in (None,0):
                stats["no_valid_trade"]+=1
                if len(invalid_samples)<8:
                    invalid_samples.append({"symbol":code,"market":m.get("exchange"),
                      "z":q.get("z"),"pz":q.get("pz"),"tv":q.get("tv"),
                      "o":q.get("o"),"h":q.get("h"),"l":q.get("l"),
                      "v":q.get("v"),"t":q.get("t"),"y":q.get("y")})
                continue
            vol=_i(q.get("v"))
            rows_by_symbol[code]={**m,"name":q.get("n") or m.get("name",""),
                "last":last,"previous_close":prev,
                "change_pct":(last/prev-1)*100,
                "volume":vol,"trade_value":last*vol*1000,
                "high":_f(q.get("h")),"low":_f(q.get("l")),"open":_f(q.get("o")),
                "bid":_f((q.get("b") or "").split("_")[0]),
                "ask":_f((q.get("a") or "").split("_")[0]),
                "quote_date":q.get("d"),"quote_time":q.get("t",""),"quote_source":"TWSE MIS"}

    missing=[]
    invalid_samples=[]
    stats["initial_missing_response"]=0
    stats["initial_present_without_executed_price"]=0
    # Probe whether the provider's blank-z response is a large-batch artifact.
    # Only use adaptive small requests after a real 8-symbol probe recovers
    # executed prices. This is not a license to fabricate or certify quotes.
    offset=0
    effective_batch_size=batch_size
    adaptive_probe_done=False
    adaptive_started=time.monotonic()
    adaptive_failure_streak=0
    stats["adaptive_probe_valid"]=0
    stats["adaptive_small_batch_enabled"]=False
    stats["adaptive_disabled_reason"]=None
    while offset<len(universe):
        if effective_batch_size<batch_size and time.monotonic()-adaptive_started>120:
            effective_batch_size=batch_size
            stats["adaptive_disabled_reason"]="TIME_BUDGET_EXCEEDED"
        batch=universe[offset:offset+effective_batch_size]
        offset+=len(batch)
        meta={x["symbol"]:x for x in batch}
        prior_failures=stats["failed_requests"]
        arr=request(batch)
        adaptive_failure_streak=(adaptive_failure_streak+1 if
            stats["failed_requests"]>prior_failures else 0)
        if adaptive_failure_streak>=3 and effective_batch_size<batch_size:
            effective_batch_size=batch_size
            stats["adaptive_disabled_reason"]="PROVIDER_ERROR_CIRCUIT_BREAKER"
        responded={str(q.get("c","")).strip() for q in arr}
        stats["initial_missing_response"]+=sum(
            x["symbol"] not in responded for x in batch
        )
        stats["initial_present_without_executed_price"]+=sum(
            q.get("c") in meta and
            (_f(q.get("z")) is None or _f(q.get("y")) in (None,0))
            for q in arr
        )
        ingest(arr,meta)
        missing.extend(x for x in batch if x["symbol"] not in rows_by_symbol)
        # In large universes, use one small *real trade* probe to distinguish
        # loss caused by MIS batch size from persistent missing executions.
        if (not adaptive_probe_done and len(universe)>=400
            and batch_size>8 and len(batch)>8
            and len(missing)>=int(len(batch)*0.7)):
            adaptive_probe_done=True
            probe=missing[:8]
            if len(probe)==8:
                stats["recovery_requested"]+=len(probe)
                recovered=request(probe,recovery=True)
                ingest(recovered,{x["symbol"]:x for x in probe})
                gained=sum(x["symbol"] in rows_by_symbol for x in probe)
                stats["adaptive_probe_valid"]=gained
                if gained>=6:
                    effective_batch_size=8
                    stats["adaptive_small_batch_enabled"]=True
        time.sleep(sleep_s)

    # Do not recover the same symbols twice after a successful probe.
    missing=[x for x in missing if x["symbol"] not in rows_by_symbol]

    # One bounded recovery pass: the MIS endpoint may silently truncate ex_ch.
    # A recovery chunk of 8 keeps the query short; no infinite retries.
    # Bounded diagnostic recovery: do not flood MIS when z is unavailable
    # across most of the market. This is NOT a substitute for licensed quotes.
    recovery_size=8
    recovery_limit=80
    sample_step=max(1, (len(missing)+recovery_limit-1)//recovery_limit)
    sampled_missing=missing[::sample_step][:recovery_limit]
    stats["recovery_skipped"]=len(missing)-len(sampled_missing)
    consecutive_failures=0
    for i in range(0,len(sampled_missing),recovery_size):
        batch=sampled_missing[i:i+recovery_size]
        stats["recovery_requested"]+=len(batch)
        prior_failures=stats["failed_requests"]
        arr=request(batch,recovery=True)
        if stats["failed_requests"]>prior_failures:
            consecutive_failures+=1
        else:
            consecutive_failures=0
        ingest(arr,{x["symbol"]:x for x in batch})
        if consecutive_failures>=3:
            stats["recovery_stopped_after_failures"]=True
            warnings.append("MIS_RECOVERY_CIRCUIT_BREAKER: three consecutive failures")
            break
        time.sleep(sleep_s)

    # Exchange-aware observability only. Never change qualification of a
    # source quote merely to improve a coverage metric.
    for exchange in ("TWSE", "TPEx"):
        target_symbols = {
            str(x["symbol"]) for x in universe
            if x.get("exchange") == exchange
        }
        valid_symbols = target_symbols.intersection(rows_by_symbol)
        stats[f"{exchange.lower()}_requested"] = len(target_symbols)
        stats[f"{exchange.lower()}_valid_trade"] = len(valid_symbols)
        stats[f"{exchange.lower()}_coverage_pct"] = round(
            len(valid_symbols) * 100.0 / len(target_symbols), 2
        ) if target_symbols else 0.0
    warnings.append(
        "MIS_EXCHANGE_COVERAGE: "
        + ", ".join(
            f"{exchange}={stats[f'{exchange.lower()}_valid_trade']}"
            f"/{stats[f'{exchange.lower()}_requested']}"
            f" ({stats[f'{exchange.lower()}_coverage_pct']}%)"
            for exchange in ("TWSE", "TPEx")
        )
    )
    stats["missing_after_recovery"]=len(universe)-len(rows_by_symbol)
    stats["recovery_valid_quotes"]=sum(
        x["symbol"] in rows_by_symbol for x in missing
    )
    warnings.append("MIS_INVALID_PRICE_SAMPLES: "+repr(invalid_samples))
    warnings.append("MIS_COVERAGE_DIAGNOSTICS: "+", ".join(f"{k}={v}" for k,v in stats.items()))
    if len(universe)>0 and len(rows_by_symbol)/len(universe)<0.80:
        warnings.append("MIS_LOW_COVERAGE: data incomplete; must not certify full-market scan")
    return list(rows_by_symbol.values()),warnings


def fetch_fugle_snapshot_quotes(universe, trading_date=None):
    """Bulk live quotes (TSE/OTC), with strict date and executed-trade checks.

    This is an optional permission-dependent source. Never substitute reference,
    bid, ask, or prior-close values for an absent last-traded price.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from .fugle import snapshot_quotes

    today=trading_date or datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat()
    by_market={"TSE":{},"OTC":{}}
    for item in universe:
        by_market.get(item.get("market"),{}).update({str(item["symbol"]):item})
    rows=[]
    warnings=[]
    for market in ("TSE","OTC"):
        targets=by_market[market]
        if not targets:
            continue
        try:
            payload=snapshot_quotes(market)
            date=str(payload.get("date") or "")
            arr=payload.get("data")
            if date!=today or not isinstance(arr,list):
                warnings.append(f"FUGLE_SNAPSHOT_STALE_OR_INVALID {market}: date={date}, expected={today}")
                continue
            retained=0
            for q in arr:
                symbol=str(q.get("symbol") or "")
                meta=targets.get(symbol)
                if not meta or q.get("isTrial") is True:
                    continue
                volume=_i(q.get("tradeVolume"))
                last=_f(q.get("lastPrice"))
                # closePrice may be a reference/closing field, not evidence of
                # a current executed trade. Never use it as lastPrice.
                delta=_f(q.get("change"))
                prev=_f(q.get("previousClose"))
                if prev is None and last is not None and delta is not None:
                    prev=last-delta
                if last is None or prev in (None,0) or volume<=0:
                    continue
                rows.append({**meta,"name":q.get("name") or meta.get("name",""),
                    "last":last,"previous_close":prev,
                    "change_pct":(last/prev-1)*100,
                    "volume":volume,"trade_value":_f(q.get("tradeValue")) or 0,
                    "high":_f(q.get("highPrice")),"low":_f(q.get("lowPrice")),
                    "open":_f(q.get("openPrice")),
                    "bid":None,"ask":None,
                    "quote_date": date,
                    "last_trade_timestamp": (
                        (q.get("lastTrade") or {}).get("time")
                        if isinstance(q.get("lastTrade"), dict)
                        else q.get("closeTime")
                    ),
                    "quote_time":str(q.get("lastUpdated") or payload.get("time") or ""),
                    "quote_source":"Fugle bulk snapshot"})
                retained+=1
            warnings.append(f"FUGLE_SNAPSHOT {market}: returned={len(arr)}, valid={retained}, universe={len(targets)}")
        except Exception as exc:
            warnings.append(f"FUGLE_SNAPSHOT_UNAVAILABLE {market}: {type(exc).__name__}: {str(exc)[:150]}")
    return rows,warnings
