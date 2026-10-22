"""Official-source layer.

TWSE universe: TWSE OpenAPI STOCK_DAY_ALL.
TPEx universe: TPEx OpenAPI tpex_mainboard_quotes.
Intraday quotes: TWSE MIS supports both TSE and OTC symbols. For OTC this is an
operational fallback, NOT a TPEx-official intraday source. STRICT_OFFICIAL_MODE
therefore never certifies a complete full-market scan from MIS-OTC alone.
"""
import re, time
from .http import get_json, session

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

def fetch_mis_quotes(universe,batch_size=55,sleep_s=.18):
    s=session(); s.headers.update({"Referer":"https://mis.twse.com.tw/stock/index.jsp"})
    try: s.get("https://mis.twse.com.tw/stock/index.jsp",timeout=15)
    except Exception: pass
    rows=[]; warnings=[]
    for i in range(0,len(universe),batch_size):
        batch=universe[i:i+batch_size]
        ex_ch="|".join(f'{x["mis_prefix"]}_{x["symbol"]}.tw' for x in batch)
        try:
            r=s.get(MIS_URL,params={"ex_ch":ex_ch,"json":"1","delay":"0"},timeout=20)
            r.raise_for_status(); payload=r.json(); arr=payload.get("msgArray",[])
        except Exception as e:
            warnings.append(f"MIS batch {i//batch_size+1} failed: {type(e).__name__}")
            continue
        meta={x["symbol"]:x for x in batch}
        for q in arr:
            code=str(q.get("c","")).strip(); m=meta.get(code)
            if not m: continue
            last=_f(q.get("z")); prev=_f(q.get("y")); vol=_i(q.get("v"))
            if last is None or prev in (None,0): continue
            rows.append({**m,"name":q.get("n") or m.get("name",""),"last":last,"previous_close":prev,
                         "change_pct":(last/prev-1)*100,"volume":vol,"trade_value":last*vol*1000,
                         "high":_f(q.get("h")),"low":_f(q.get("l")),"open":_f(q.get("o")),
                         "bid":_f((q.get("b") or "").split("_")[0]),"ask":_f((q.get("a") or "").split("_")[0]),
                         "quote_time":q.get("t", ""),"quote_source":"TWSE MIS"})
        time.sleep(sleep_s)
    return rows,warnings
