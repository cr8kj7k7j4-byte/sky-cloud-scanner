from __future__ import annotations

import json
import re
import requests
from pathlib import Path

BASE = "https://www.tpex.org.tw"
ASSETS = [
    "/rsrc/js/tables.js",
    "/rsrc/asset/js/global.js",
    "/rsrc/js/main.js",
]

def fetch(path):
    r=requests.get(
        BASE+path,
        timeout=30,
        headers={
            "User-Agent":"Mozilla/5.0 SkyResearchBot/1.0",
            "Referer":"https://www.tpex.org.tw/zh-tw/mainboard/listed/delisted.html",
        },
    )
    r.raise_for_status()
    r.encoding=r.apparent_encoding or r.encoding
    return r.text

def main():
    out=Path("output/tpex_api_probe")
    out.mkdir(parents=True,exist_ok=True)
    report={"assets":[]}
    for path in ASSETS:
        item={"path":path}
        try:
            text=fetch(path)
            name=path.rsplit("/",1)[-1]
            (out/name).write_text(text,encoding="utf-8")
            item["size"]=len(text)
            item["api_pattern_snippets"]=[
                text[max(0,m.start()-300):m.start()+800]
                for m in list(re.finditer(r"API_PATTERN",text))[:20]
            ]
            item["company_delisted_snippets"]=[
                text[max(0,m.start()-300):m.start()+800]
                for m in list(re.finditer(r"company/deListed|deListed",text,re.I))[:20]
            ]
            item["urls"]=sorted(set(re.findall(
                r'https?://[^"\'<> ]+|/[A-Za-z0-9_./?=&-]+',
                text
            )))[:500]
        except Exception as exc:
            item["error"]=f"{type(exc).__name__}: {exc}"
        report["assets"].append(item)
    (out/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
