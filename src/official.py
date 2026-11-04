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
            stats["failed_requests"]+=1
            if sum("batch failed" in w for w in warnings)<5:
                warnings.append(f"MIS {'recovery' if recovery else 'initial'} batch failed: {type(e).__name__}: {str(e)[:120]}")
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
                "quote_time":q.get("t",""),"quote_source":"TWSE MIS"}

    missing=[]
    invalid_samples=[]
    # First pass: retain original batches for throughput.
    for i in range(0,len(universe),batch_size):
        batch=universe[i:i+batch_size]
        meta={x["symbol"]:x for x in batch}
        arr=request(batch)
        ingest(arr,meta)
        # A response can contain a symbol while z='-'. Such symbols still lack
        # a verified executed price and must be retried in a smaller request.
        missing.extend(x for x in batch if x["symbol"] not in rows_by_symbol)
        time.sleep(sleep_s)

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

    stats["missing_after_recovery"]=len(universe)-len(rows_by_symbol)
    stats["recovery_valid_quotes"]=len(rows_by_symbol) - (stats["initial_requested"] - len(missing))
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
                    "quote_time":str(q.get("lastUpdated") or payload.get("time") or ""),
                    "quote_source":"Fugle bulk snapshot"})
                retained+=1
            warnings.append(f"FUGLE_SNAPSHOT {market}: returned={len(arr)}, valid={retained}, universe={len(targets)}")
        except Exception as exc:
            warnings.append(f"FUGLE_SNAPSHOT_UNAVAILABLE {market}: {type(exc).__name__}: {str(exc)[:150]}")
    return rows,warnings
