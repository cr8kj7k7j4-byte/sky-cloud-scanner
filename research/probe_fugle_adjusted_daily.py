from __future__ import annotations
import json, os, sys
import requests

BASE="https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/2330"
key=os.getenv("FUGLE_API_KEY","").strip()
if not key:
    print(json.dumps({"ok":False,"reason":"FUGLE_API_KEY_NOT_AVAILABLE"}))
    raise SystemExit(2)

params={
    "from":"2026-01-02",
    "to":"2026-01-09",
    "timeframe":"D",
    "adjusted":"true",
    "fields":"open,high,low,close,volume,turnover,change",
    "sort":"asc",
}
r=requests.get(BASE,params=params,headers={"X-API-KEY":key,"User-Agent":"Sky-W3-Price-Probe/1.0"},timeout=30)
safe={"status_code":r.status_code}
try:
    body=r.json()
    safe["error_message"]=body.get("message") or body.get("error")
    safe["symbol"]=body.get("symbol")
    safe["adjusted"]=body.get("adjusted")
    safe["bars"]=len(body.get("data") or [])
except Exception:
    safe["body_prefix"]=r.text[:120]
print(json.dumps(safe,ensure_ascii=False))
if r.status_code!=200 or safe.get("bars",0)<1 or safe.get("adjusted") is not True:
    raise SystemExit(3)
