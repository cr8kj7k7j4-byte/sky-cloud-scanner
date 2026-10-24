from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from typing import Iterable

import requests
from bs4 import BeautifulSoup

MOPS_HISTORY = "https://mopsov.twse.com.tw/mops/web/t05st01"
HEADERS = {
    "User-Agent": "Mozilla/5.0 SkyPremarket/1.0",
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
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"MOPS {symbol}/{roc_year}: {err}")

def parse_company_year(html: str, symbol: str) -> list[dict]:
    if "查無資料" in html or "查無" in html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for tr in soup.find_all("tr"):
        cells = [x.get_text(" ", strip=True) for x in tr.find_all(["th", "td"], recursive=False)]
        if len(cells) < 5:
            continue
        if cells[0] != str(symbol):
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
            "source": "MOPS",
            "source_url": MOPS_HISTORY,
            "official": True,
        })
    seen = set()
    ans = []
    for row in out:
        key = (row["symbol"], row["announce_date"], row["announce_time"], row["subject"])
        if key not in seen:
            seen.add(key)
            ans.append(row)
    return ans

def scan_recent_events(symbols: Iterable[str], *, lookback_days: int = 3, now=None, max_symbols: int = 100):
    now = now or datetime.now()
    cutoff = now.date() - timedelta(days=max(1, lookback_days))
    sess = requests.Session()
    events, errors = [], []
    symbols = [str(s) for s in symbols][:max_symbols]
    years = {cutoff.year, now.year}
    for symbol in symbols:
        for year in sorted(years):
            try:
                html = fetch_company_year(sess, symbol, year - 1911)
                for event in parse_company_year(html, symbol):
                    d = datetime.fromisoformat(event["announce_date"]).date()
                    if cutoff <= d <= now.date():
                        events.append(event)
            except Exception as exc:
                errors.append({"symbol": symbol, "year": year, "error": f"{type(exc).__name__}: {exc}"})
    events.sort(key=lambda x: (x["announce_date"], x["announce_time"], x["symbol"]), reverse=True)
    return events, errors
