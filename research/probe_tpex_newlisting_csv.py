from __future__ import annotations

import json
import requests
from pathlib import Path

BASE="https://www.tpex.org.tw"

def decode(raw):
    for enc in ("utf-8-sig","utf-8","big5","cp950"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8",errors="ignore")

def main():
    out=Path("output/tpex_newlisting_csv_probe")
    out.mkdir(parents=True,exist_ok=True)
    report={}
    for year in (2005,2010,2020,2023,2026):
        url=f"{BASE}/www/zh-tw/company/applicantStatDl?type=list&date={year}"
        r=requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent":"Mozilla/5.0 SkyResearchBot/1.0",
                "Referer":"https://www.tpex.org.tw/zh-tw/mainboard/applying/status/new-listed.html",
            },
        )
        r.raise_for_status()
        text=decode(r.content)
        (out/f"{year}.csv").write_text(text,encoding="utf-8")
        lines=text.splitlines()
        report[str(year)]={
            "status":r.status_code,
            "content_type":r.headers.get("content-type"),
            "bytes":len(r.content),
            "first_lines":lines[:12],
        }
    (out/"summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
