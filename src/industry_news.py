from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

import requests

GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"
UA = {"User-Agent": "Mozilla/5.0 SkyIndustryNews/1.0"}

OFFICIAL_DOMAINS = {
    "nvidia.com": 95,
    "nvidianews.nvidia.com": 95,
    "amd.com": 95,
    "newsroom.amd.com": 95,
    "intel.com": 95,
    "newsroom.intel.com": 95,
    "tsmc.com": 100,
    "micron.com": 95,
    "samsung.com": 90,
    "news.samsung.com": 90,
    "skhynix.com": 95,
}
TRUSTED_MEDIA = {
    "reuters.com": 85,
    "apnews.com": 80,
    "bloomberg.com": 80,
}
QUERY = '(semiconductor OR "AI chip" OR HBM OR foundry OR GPU OR "data center" OR memory OR DRAM OR NAND)'

SECTOR_KEYWORDS = {
    "SEMICONDUCTOR": ("semiconductor", "foundry", "wafer", "chip", "hbm", "dram", "nand", "memory"),
    "AI_SERVER": ("gpu", "ai chip", "data center", "accelerator", "server", "hbm"),
    "DISPLAY": ("display", "panel", "oled", "lcd"),
}

def _domain(url):
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host

def _authority(domain):
    for d, score in OFFICIAL_DOMAINS.items():
        if domain == d or domain.endswith("." + d):
            return "OFFICIAL_COMPANY", score
    for d, score in TRUSTED_MEDIA.items():
        if domain == d or domain.endswith("." + d):
            return "TRUSTED_MEDIA", score
    return None, 0

def _sectors(title):
    t = (title or "").lower()
    out = []
    for sector, words in SECTOR_KEYWORDS.items():
        if any(w in t for w in words):
            out.append(sector)
    return out

def _parse_seen(value):
    if not value:
        return None
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt).isoformat() + "Z"
        except ValueError:
            pass
    return str(value)

def fetch_industry_news(*, timespan="24H", maxrecords=100):
    params = {
        "query": QUERY,
        "mode": "artlist",
        "maxrecords": str(maxrecords),
        "format": "json",
        "sort": "DateDesc",
        "timespan": timespan,
    }
    r = requests.get(GDELT_DOC, params=params, headers=UA, timeout=45)
    r.raise_for_status()
    payload = r.json()

    articles = payload.get("articles") or []
    accepted, rejected = [], 0
    seen = set()

    for a in articles:
        url = a.get("url") or ""
        title = (a.get("title") or "").strip()
        domain = _domain(url)
        tier, score = _authority(domain)
        if not tier or not title:
            rejected += 1
            continue

        key = (domain, title.lower())
        if key in seen:
            continue
        seen.add(key)

        sectors = _sectors(title)
        if not sectors:
            rejected += 1
            continue

        accepted.append({
            "symbol": "GLOBAL",
            "name": domain,
            "announce_date": "",
            "announce_time": "",
            "published_at": _parse_seen(a.get("seendate")),
            "subject": title,
            "event_type": "INDUSTRY_NEWS",
            "event_role": "INDUSTRY_EVIDENCE",
            "source": domain,
            "source_tier": tier,
            "authority_score": score,
            "source_url": url,
            "official": tier == "OFFICIAL_COMPANY",
            "affected_sectors": sectors,
            "trade_signal": False,
            "note": "新聞僅作 P0-K/P0-EVT 證據，不直接形成交易訊號",
        })

    return {
        "status": "CONNECTED",
        "provider": "GDELT_DISCOVERY",
        "query": QUERY,
        "timespan": timespan,
        "accepted_count": len(accepted),
        "rejected_count": rejected,
        "articles": accepted,
        "trade_signal": False,
        "note": "GDELT 僅負責發現；正式納入前必須通過來源白名單",
    }
