"""Non-trading disclosure source discovery (TWSE IIH2 SSR vs client-rendered).

The existence of a heading named 公告日期時間 is not proof that issuer event
rows, historical coverage, or an accessible publication API exist.
No claim of TPEx equivalence; no inferred source or order execution.
"""
from __future__ import annotations
import argparse
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PAGES = {
    "TWSE_INFORMATION_MARKET": "https://www.twse.com.tw/IIH2/zh/market/information.html",
    "TWSE_INFORMATION_1216": "https://www.twse.com.tw/IIH2/zh/company/information.html?code=1216",
    "TWSE_INFORMATION_2330": "https://www.twse.com.tw/IIH2/zh/company/information.html?code=2330",
}
TW_DATE = re.compile(r"(?:11[2-5]|20(?:2[3-6]))[/.-](?:0?[1-9]|1[0-2])[/.-](?:[0-2]?\d|3[01])\s+(?:[01]?\d|2[0-3]):[0-5]\d")
ANNOUNCEMENT = "公告日期時間"


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.scripts = []
    def handle_data(self, data):
        chunk = " ".join(data.split())
        if chunk:
            self.text.append(chunk)
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            for key, value in attrs:
                if key == "src" and value:
                    self.scripts.append(value)


def analyze_html(raw: str) -> dict:
    doc = PageText()
    doc.feed(raw)
    txt = " ".join(doc.text)
    matches = sorted(set(TW_DATE.findall(txt)))
    return {
        "has_announcement_datetime_heading": ANNOUNCEMENT in txt,
        "candidate_datetime_strings_in_rendered_html": len(matches),
        "candidate_datetime_samples": matches[:3],
        "script_asset_count": len(doc.scripts),
        "source_timestamps_qualified": False,
        "historical_issuer_filing_coverage_certified": False,
        "reason": "HTML text/time strings or JS assets are not independently verified filing-level historical disclosure records."
    }


def probe(url: str) -> dict:
    try:
        req = Request(url, headers={"User-Agent": "SkyPITDisclosureAudit/1.0"})
        with urlopen(req, timeout=16) as res:
            body = res.read(3_500_000)
            status = res.status
            ctype = res.headers.get("Content-Type", "")
        text = body.decode("utf-8-sig", errors="replace")
        result = analyze_html(text)
        result.update({"http_status": status, "content_type": ctype, "bytes_read": len(body)})
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        result = {"error": type(exc).__name__+": "+str(exc)[:150],
                  "source_timestamps_qualified": False,
                  "historical_issuer_filing_coverage_certified": False}
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="research_output/disclosure_source_discovery.json")
    args=ap.parse_args()
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "INSUFFICIENT_DATA",
        "production_signal": False,
        "scope": "TWSE selected official web pages only, not TPEx or MOPS historical whole universe",
        "sources": {label: probe(url) for label, url in PAGES.items()},
        "unresolved": [
            "Official issuer-level historical published_at, original filing document and source ID",
            "Distinguish disclosure category from monthly revenue announcements",
            "Historical completeness, pagination, timestamp timezone, re-issue duplicates and corrections",
            "TPEx issuer-level historical API/official records and lawful bulk access",
            "Release-to-trading-decision latency and time-aware vendor archival proof",
        ]
    }
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
