import requests
from .config import FUGLE_API_KEY
BASE="https://api.fugle.tw/marketdata/v1.0/stock"

def _headers():
    if not FUGLE_API_KEY: raise RuntimeError("Missing FUGLE_API_KEY")
    return {"X-API-KEY":FUGLE_API_KEY,"User-Agent":"SkyCloudScanner/0.3"}

def _get(path,params=None):
    r=requests.get(f"{BASE}{path}",params=params,headers=_headers(),timeout=20)
    r.raise_for_status(); return r.json()

def get_ticker(symbol): return _get(f"/intraday/ticker/{symbol}")
def get_quote(symbol): return _get(f"/intraday/quote/{symbol}")
def get_candles(symbol,timeframe="5"): return _get(f"/intraday/candles/{symbol}",{"timeframe":timeframe,"sort":"asc"})
def snapshot_quotes(market): return _get(f"/snapshot/quotes/{market}",{"type":"COMMONSTOCK"})
def snapshot_movers(market): return _get(f"/snapshot/movers/{market}",{"direction":"up","change":"percent","type":"COMMONSTOCK"})
def snapshot_actives(market,trade="value"): return _get(f"/snapshot/actives/{market}",{"trade":trade,"type":"COMMONSTOCK"})
