from __future__ import annotations

import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

BIS_NEWS_URL = "https://www.bis.gov/news-updates"
UA = {"User-Agent": "Mozilla/5.0 SkyPremarketPolicy/1.0"}

KEYWORDS = (
    "semiconductor",
    "artificial intelligence",
    "advanced computing",
    "ai chip",
    "chips",
    "export control",
    "entity list",
    "hbm",
    "china",
)

def _parse_date(text: str):
    text = (text or "").strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None

def fetch_recent_bis_policy_events(now=None, lookback_days=14):
    now = now or datetime.now()
    cutoff = now.date() - timedelta(days=max(1, lookback_days))
    r = requests.get(BIS_NEWS_URL, headers=UA, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [x.strip() for x in text.splitlines() if x.strip()]

    out = []
    current_date = None
    date_re = re.compile(r"^[A-Z][a-z]+ \d{1,2}, \d{4}$")
    for line in lines:
        if date_re.match(line):
            d = _parse_date(line)
            if d:
                current_date = d
            continue
        if current_date is None or current_date < cutoff or current_date > now.date():
            continue
        low = line.lower()
        if not any(k in low for k in KEYWORDS):
            continue
        if len(line) < 18 or len(line) > 260:
            continue
        out.append({
            "symbol": "GLOBAL",
            "name": "U.S. BIS",
            "announce_date": str(current_date),
            "announce_time": "",
            "subject": line,
            "event_type": "EXPORT_CONTROL_POLICY",
            "event_role": "MACRO_POLICY_EVENT",
            "source": "BIS",
            "source_url": BIS_NEWS_URL,
            "official": True,
            "trade_signal": False,
            "affected_sectors": ["SEMICONDUCTOR", "AI_SERVER"],
            "note": "官方政策事件僅作風險/催化背景，不直接代表多空方向",
        })

    seen, ans = set(), []
    for row in out:
        key = (row["announce_date"], row["subject"])
        if key not in seen:
            seen.add(key)
            ans.append(row)

    ans.sort(key=lambda x: (x["announce_date"], x["subject"]), reverse=True)
    return ans
