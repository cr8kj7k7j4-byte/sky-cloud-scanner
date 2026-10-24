from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

FRED_DGS10_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
FRED_SP500_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500"
FRED_NASDAQ_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=NASDAQCOM"
FRED_WTI_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILWTICO"
CBC_NTDUSD_API = "https://cpx.cbc.gov.tw/API/DataAPI/Get?FileName=BP01D01en"
CBOE_VIX_CSV = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"
FED_FOMC_YEAR = "https://www.federalreserve.gov/newsevents/pressreleases/{year}-press-fomc.htm"
UA = {"User-Agent": "Mozilla/5.0 SkyPremarketGlobal/1.0"}

def _get_text(url, timeout=30):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r.text

def _latest_numeric_csv(text, date_col_candidates, value_col_candidates):
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return None
    for row in reversed(rows):
        date_key = next((k for k in date_col_candidates if k in row), None)
        value_key = next((k for k in value_col_candidates if k in row), None)
        if not date_key or not value_key:
            continue
        raw = str(row.get(value_key) or "").strip()
        if raw in {"", ".", "NA", "nan"}:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        return {"date": str(row.get(date_key) or "").strip(), "value": value}
    return None

def fetch_us10y():
    text = _get_text(FRED_DGS10_CSV)
    latest = _latest_numeric_csv(text, ("DATE", "observation_date"), ("DGS10",))
    if not latest:
        raise RuntimeError("FRED DGS10 has no usable observation")
    return {
        "key": "US10Y",
        "name": "美國10年期公債殖利率",
        "value": latest["value"],
        "unit": "%",
        "as_of": latest["date"],
        "source": "FRED",
        "source_url": FRED_DGS10_CSV,
        "official": True,
        "trade_signal": False,
    }

def fetch_fred_market_series(key, name, url, unit):
    text = _get_text(url)
    series_id = url.split("id=")[-1]
    latest = _latest_numeric_csv(text, ("DATE", "observation_date"), (series_id,))
    if not latest:
        raise RuntimeError(f"FRED {series_id} has no usable observation")
    return {
        "key": key,
        "name": name,
        "value": latest["value"],
        "unit": unit,
        "as_of": latest["date"],
        "source": "FRED",
        "source_url": url,
        "official": True,
        "trade_signal": False,
    }

def _walk_json(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk_json(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_json(v)

def fetch_ntdusd():
    r = requests.get(CBC_NTDUSD_API, headers=UA, timeout=30)
    r.raise_for_status()
    payload = r.json()
    candidates = []
    for row in _walk_json(payload):
        keys = {str(k).lower(): k for k in row.keys()}
        date_key = next((orig for low, orig in keys.items() if low in {"period", "date"} or "period" in low), None)
        ntd_key = next((orig for low, orig in keys.items() if ("ntd" in low and "usd" in low) or "新台幣" in low), None)
        if not date_key or not ntd_key:
            continue
        raw = str(row.get(ntd_key) or "").replace(",", "").strip()
        if raw in {"", ".", "NA"}:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        candidates.append((str(row.get(date_key) or ""), value))
    if not candidates:
        raise RuntimeError("CBC NTD/USD API has no usable observation")
    candidates.sort(key=lambda x: x[0])
    date, value = candidates[-1]
    return {
        "key": "NTDUSD",
        "name": "新台幣兌美元",
        "value": value,
        "unit": "NTD per USD",
        "as_of": date,
        "source": "CBC_TAIWAN",
        "source_url": CBC_NTDUSD_API,
        "official": True,
        "trade_signal": False,
    }

def fetch_vix():
    text = _get_text(CBOE_VIX_CSV)
    latest = _latest_numeric_csv(
        text,
        ("DATE", "Date"),
        ("CLOSE", "Close", "close"),
    )
    if not latest:
        raise RuntimeError("Cboe VIX has no usable observation")
    value = latest["value"]
    if value >= 35:
        regime = "EXTREME"
    elif value >= 25:
        regime = "HIGH"
    elif value >= 18:
        regime = "ELEVATED"
    else:
        regime = "NORMAL"
    return {
        "key": "VIX",
        "name": "Cboe VIX",
        "value": value,
        "unit": "index",
        "as_of": latest["date"],
        "risk_regime": regime,
        "source": "CBOE",
        "source_url": CBOE_VIX_CSV,
        "official": True,
        "trade_signal": False,
    }

def fetch_recent_fomc(now=None, lookback_days=7):
    now = now or datetime.now()
    url = FED_FOMC_YEAR.format(year=now.year)
    html = _get_text(url)
    soup = BeautifulSoup(html, "html.parser")
    cutoff = now.date() - timedelta(days=max(1, lookback_days))
    out = []

    text = soup.get_text("\n", strip=True)
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    date_re = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
    for i, line in enumerate(lines):
        m = date_re.match(line)
        if not m:
            continue
        mo, d, y = map(int, m.groups())
        try:
            event_date = datetime(y, mo, d).date()
        except ValueError:
            continue
        if not (cutoff <= event_date <= now.date()):
            continue
        title = ""
        for j in range(i + 1, min(i + 5, len(lines))):
            candidate = lines[j]
            if date_re.match(candidate):
                break
            if candidate.lower() != "monetary policy" and len(candidate) >= 12:
                title = candidate
                break
        if title:
            out.append({
                "symbol": "GLOBAL",
                "name": "Federal Reserve",
                "announce_date": str(event_date),
                "announce_time": "",
                "subject": title,
                "event_type": "MONETARY_POLICY",
                "event_role": "MACRO_EVENT",
                "source": "FEDERAL_RESERVE",
                "source_url": url,
                "official": True,
                "trade_signal": False,
            })
    seen, ans = set(), []
    for row in out:
        key = (row["announce_date"], row["subject"])
        if key not in seen:
            seen.add(key)
            ans.append(row)
    return ans

def build_global_context(now=None, lookback_days=7):
    now = now or datetime.now()
    indicators = []
    macro_events = []
    health = {}
    errors = []

    market_fetchers = (
        ("FRED_US10Y", fetch_us10y),
        ("CBOE_VIX", fetch_vix),
        ("FRED_SP500", lambda: fetch_fred_market_series("SP500", "S&P 500", FRED_SP500_CSV, "index")),
        ("FRED_NASDAQ", lambda: fetch_fred_market_series("NASDAQCOM", "Nasdaq Composite", FRED_NASDAQ_CSV, "index")),
        ("FRED_WTI", lambda: fetch_fred_market_series("WTI", "WTI原油", FRED_WTI_CSV, "USD/barrel")),
        ("CBC_NTDUSD", fetch_ntdusd),
    )
    for name, fn in market_fetchers:
        try:
            data = fn()
            indicators.append(data)
            health[name] = {"ok": True, "as_of": data.get("as_of")}
        except Exception as exc:
            health[name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            errors.append({"source": name, "error": health[name]["error"]})

    try:
        macro_events = fetch_recent_fomc(now=now, lookback_days=lookback_days)
        health["FED_FOMC"] = {"ok": True, "events": len(macro_events)}
    except Exception as exc:
        health["FED_FOMC"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        errors.append({"source": "FED_FOMC", "error": health["FED_FOMC"]["error"]})

    vix = next((x for x in indicators if x["key"] == "VIX"), None)
    us10y = next((x for x in indicators if x["key"] == "US10Y"), None)
    sp500 = next((x for x in indicators if x["key"] == "SP500"), None)
    nasdaq = next((x for x in indicators if x["key"] == "NASDAQCOM"), None)
    wti = next((x for x in indicators if x["key"] == "WTI"), None)
    ntdusd = next((x for x in indicators if x["key"] == "NTDUSD"), None)

    risk_state = "UNKNOWN"
    if vix:
        risk_state = vix.get("risk_regime", "UNKNOWN")

    return {
        "generated_at": now.isoformat(),
        "indicators": indicators,
        "macro_events": macro_events,
        "source_health": health,
        "risk_state": risk_state,
        "us10y": us10y,
        "vix": vix,
        "sp500": sp500,
        "nasdaq": nasdaq,
        "wti": wti,
        "ntdusd": ntdusd,
        "trade_signal": False,
        "coverage": {
            "vix": bool(vix),
            "us10y": bool(us10y),
            "fomc": health.get("FED_FOMC", {}).get("ok", False),
            "us_equity_index": bool(sp500 and nasdaq),
            "taiwan_adr": False,
            "fx_usdtwd": bool(ntdusd),
            "commodity_wti": bool(wti),
            "commodity_gold": False,
            "industry_news": False,
        },
        "warnings": [
            "全球背景層目前涵蓋 VIX、US10Y、S&P500、Nasdaq Composite、NTD/USD、WTI 與 FOMC；"
            "台灣ADR、黃金與產業新聞尚未接通，一律視為 NOT_CONNECTED。"
        ],
        "errors": errors,
    }
