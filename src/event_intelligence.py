from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Iterable

import requests
from bs4 import BeautifulSoup

MOPS_HISTORY = "https://mopsov.twse.com.tw/mops/web/t05st01"
TWSE_NOTICE = "https://www.twse.com.tw/rwd/zh/announcement/notice"
TWSE_DISPOSAL = "https://www.twse.com.tw/rwd/zh/announcement/punish"
TPEX_ATTENTION = "https://www.tpex.org.tw/www/zh-tw/bulletin/attention"
TPEX_DISPOSAL = "https://www.tpex.org.tw/www/zh-tw/bulletin/disposal"

HEADERS = {
    "User-Agent": "Mozilla/5.0 SkyPremarket/1.1",
    "Referer": MOPS_HISTORY,
}

CATEGORY_RULES = [
    ("EARNINGS", ("每股盈餘", "財務報告", "財報", "盈餘")),
    ("REVENUE", ("營收",)),
    ("GUIDANCE", ("財測", "展望", "預估", "forecast", "guidance")),
    ("INVESTOR_EVENT", ("法人說明會", "法說", "投資人說明會")),
    ("CONTRACT_ORDER", ("訂單", "合約", "標案", "得標", "新藥", "授權")),
    ("CORPORATE_ACTION", ("股利", "增資", "減資", "庫藏股", "合併", "分割", "併購", "處分", "取得資產")),
]

def _normalize_date(value: str):
    value = (value or "").strip().replace("年", "/").replace("月", "/").replace("日", "")
    m = re.search(r"(\d{3,4})[/-](\d{1,2})[/-](\d{1,2})", value)
    if not m:
        return None
    y, mo, d = map(int, m.groups())
    if y < 1911:
        y += 1911
    try:
        return datetime(y, mo, d).date()
    except ValueError:
        return None

def classify_event(subject: str) -> str:
    s = (subject or "").lower()
    for category, keywords in CATEGORY_RULES:
        if any(k.lower() in s for k in keywords):
            return category
    return "OTHER"

def fetch_company_year(session: requests.Session, symbol: str, roc_year: int, retries: int = 3) -> str:
    params = {"step": "1", "firstin": "true", "year": str(roc_year), "co_id": str(symbol)}
    err = None
    for attempt in range(retries):
        try:
            r = session.get(MOPS_HISTORY, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.text
        except Exception as exc:
            err = exc
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"MOPS {symbol}/{roc_year}: {err}")

def parse_company_year(html: str, symbol: str) -> list[dict]:
    if "查無資料" in html or "查無" in html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for tr in soup.find_all("tr"):
        cells = [x.get_text(" ", strip=True) for x in tr.find_all(["th", "td"], recursive=False)]
        if len(cells) < 5 or cells[0] != str(symbol):
            continue
        d = _normalize_date(cells[2])
        if not d:
            continue
        tm = cells[3] if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", cells[3] or "") else ""
        subject = cells[4].strip()
        out.append({
            "symbol": str(symbol),
            "name": cells[1].strip(),
            "announce_date": str(d),
            "announce_time": tm,
            "subject": subject,
            "event_type": classify_event(subject),
            "event_role": "CATALYST_EVIDENCE",
            "source": "MOPS",
            "source_url": MOPS_HISTORY,
            "official": True,
            "trade_signal": False,
        })
    seen, ans = set(), []
    for row in out:
        key = (row["symbol"], row["announce_date"], row["announce_time"], row["subject"])
        if key not in seen:
            seen.add(key)
            ans.append(row)
    return ans

def _scan_one_symbol(symbol: str, years: set[int], cutoff, end_date):
    sess = requests.Session()
    rows, errors = [], []
    for year in sorted(years):
        try:
            html = fetch_company_year(sess, symbol, year - 1911)
            for event in parse_company_year(html, symbol):
                d = datetime.fromisoformat(event["announce_date"]).date()
                if cutoff <= d <= end_date:
                    rows.append(event)
        except Exception as exc:
            errors.append({"symbol": symbol, "year": year, "source": "MOPS", "error": f"{type(exc).__name__}: {exc}"})
    return rows, errors

def scan_recent_mops_events(symbols: Iterable[str], *, lookback_days: int = 3, now=None,
                            max_symbols: int = 2000, workers: int = 8):
    now = now or datetime.now()
    cutoff = now.date() - timedelta(days=max(1, lookback_days))
    symbols = [str(s) for s in symbols][:max_symbols]
    years = {cutoff.year, now.year}
    events, errors = [], []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 16))) as pool:
        futures = {pool.submit(_scan_one_symbol, s, years, cutoff, now.date()): s for s in symbols}
        for fut in as_completed(futures):
            try:
                rows, errs = fut.result()
                events.extend(rows)
                errors.extend(errs)
            except Exception as exc:
                errors.append({"symbol": futures[fut], "source": "MOPS", "error": f"{type(exc).__name__}: {exc}"})
    events.sort(key=lambda x: (x["announce_date"], x["announce_time"], x["symbol"]), reverse=True)
    return events, errors

def _json_rows(payload):
    if not isinstance(payload, dict):
        return []
    fields = payload.get("fields") or []
    data = payload.get("data") or []
    if fields and data and isinstance(data[0], list):
        return [dict(zip(fields, row)) for row in data]
    if isinstance(data, list) and (not data or isinstance(data[0], dict)):
        return data
    tables = payload.get("tables") or []
    out = []
    for tb in tables:
        fs = tb.get("fields") or []
        ds = tb.get("data") or []
        if fs and ds and isinstance(ds[0], list):
            out.extend(dict(zip(fs, row)) for row in ds)
    return out

def _first(row, names):
    for name in names:
        if row.get(name) not in (None, ""):
            return str(row.get(name)).strip()
    return ""

def _fetch_json(url, params):
    r = requests.get(url, params=params, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_twse_surveillance(now=None):
    now = now or datetime.now()
    date_ymd = now.strftime("%Y%m%d")
    events, errors = [], []
    specs = [
        ("TWSE_ATTENTION", TWSE_NOTICE, "ATTENTION"),
        ("TWSE_DISPOSAL", TWSE_DISPOSAL, "DISPOSITION"),
    ]
    for source, url, event_type in specs:
        try:
            payload = _fetch_json(url, {"response": "json", "date": date_ymd, "selectType": "ALL"})
            for row in _json_rows(payload):
                symbol = _first(row, ("證券代號", "有價證券代號", "Code", "SecuritiesCompanyCode"))
                if not re.fullmatch(r"[1-9]\d{3}", symbol):
                    continue
                name = _first(row, ("證券名稱", "有價證券名稱", "Name", "CompanyName"))
                subject = "｜".join(str(v).strip() for v in row.values() if str(v).strip())
                d = _normalize_date(_first(row, ("公布日期", "公告日期", "日期"))) or now.date()
                events.append({
                    "symbol": symbol, "name": name, "announce_date": str(d), "announce_time": "",
                    "subject": subject, "event_type": event_type, "event_role": "RISK_EVENT",
                    "source": source, "source_url": url, "official": True, "trade_signal": False,
                })
        except Exception as exc:
            errors.append({"source": source, "error": f"{type(exc).__name__}: {exc}"})
    return events, errors

def fetch_tpex_surveillance(now=None, lookback_days: int = 3):
    now = now or datetime.now()
    start = (now.date() - timedelta(days=max(1, lookback_days))).strftime("%Y/%m/%d")
    end = now.date().strftime("%Y/%m/%d")
    events, errors = [], []
    specs = [
        ("TPEX_ATTENTION", TPEX_ATTENTION, "ATTENTION"),
        ("TPEX_DISPOSAL", TPEX_DISPOSAL, "DISPOSITION"),
    ]
    for source, url, event_type in specs:
        try:
            payload = _fetch_json(url, {
                "response": "json", "startDate": start, "endDate": end,
                "type": "all", "order": "date",
            })
            for row in _json_rows(payload):
                symbol = _first(row, ("證券代號", "代號", "SecuritiesCompanyCode", "Code"))
                if not re.fullmatch(r"[1-9]\d{3}", symbol):
                    continue
                name = _first(row, ("證券名稱", "名稱", "CompanyName", "Name"))
                subject = "｜".join(str(v).strip() for v in row.values() if str(v).strip())
                d = _normalize_date(_first(row, ("公布日期", "公告日期", "日期"))) or now.date()
                events.append({
                    "symbol": symbol, "name": name, "announce_date": str(d), "announce_time": "",
                    "subject": subject, "event_type": event_type, "event_role": "RISK_EVENT",
                    "source": source, "source_url": url, "official": True, "trade_signal": False,
                })
        except Exception as exc:
            errors.append({"source": source, "error": f"{type(exc).__name__}: {exc}"})
    return events, errors

def scan_recent_events(symbols: Iterable[str], *, lookback_days: int = 3, now=None,
                       max_symbols: int = 2000, workers: int = 8):
    now = now or datetime.now()
    mops, mops_errors = scan_recent_mops_events(
        symbols, lookback_days=lookback_days, now=now,
        max_symbols=max_symbols, workers=workers,
    )
    twse, twse_errors = fetch_twse_surveillance(now=now)
    tpex, tpex_errors = fetch_tpex_surveillance(now=now, lookback_days=lookback_days)

    merged = mops + twse + tpex
    seen, events = set(), []
    for row in merged:
        key = (row.get("source"), row.get("symbol"), row.get("announce_date"),
               row.get("announce_time"), row.get("event_type"), row.get("subject"))
        if key in seen:
            continue
        seen.add(key)
        events.append(row)
    events.sort(key=lambda x: (x["announce_date"], x.get("announce_time") or "", x["symbol"]), reverse=True)
    health = {
        "MOPS": {"ok": len(mops_errors) < max(1, len(list(symbols)) // 5), "events": len(mops), "errors": len(mops_errors)},
        "TWSE_SURVEILLANCE": {"ok": not twse_errors, "events": len(twse), "errors": len(twse_errors)},
        "TPEX_SURVEILLANCE": {"ok": not tpex_errors, "events": len(tpex), "errors": len(tpex_errors)},
    }
    return events, mops_errors + twse_errors + tpex_errors, health
