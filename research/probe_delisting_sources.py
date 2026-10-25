from __future__ import annotations

import json
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path

URLS = {
    "TWSE_DELIST": "https://www.twse.com.tw/company/suspendListingCsvAndHtml?lang=zh&type=html",
    "TPEX_DELIST": "https://www.tpex.org.tw/zh-tw/mainboard/listed/delisted.html",
}

def fetch(url):
    r=requests.get(url,timeout=30,headers={"User-Agent":"Mozilla/5.0 SkyResearchBot/1.0"})
    r.raise_for_status()
    r.encoding=r.apparent_encoding or r.encoding
    return r.text

def inspect(name,text):
    soup=BeautifulSoup(text,"html.parser")
    tables=[]
    for i,t in enumerate(soup.find_all("table")):
        headers=[x.get_text(" ",strip=True) for x in t.find_all(["th","td"])[:20]]
        trs=t.find_all("tr")
        tables.append({
            "index":i,
            "rows":len(trs),
            "sample_cells":headers[:20],
        })
    forms=[]
    for i,f in enumerate(soup.find_all("form")):
        forms.append({
            "index":i,
            "action":f.get("action"),
            "method":f.get("method"),
            "inputs":[
                {
                    "name":x.get("name"),
                    "id":x.get("id"),
                    "type":x.get("type"),
                    "value":x.get("value"),
                }
                for x in f.find_all(["input","select","button"])[:100]
            ],
        })
    scripts=[x.get("src") for x in soup.find_all("script") if x.get("src")]
    apiish=sorted(set(re.findall(r'https?://[^"\'<> ]+|/[A-Za-z0-9_./?-]+(?:api|ajax|delist|list)[A-Za-z0-9_./?=&-]*',text,re.I)))
    return {
        "name":name,
        "size":len(text),
        "tables":tables,
        "forms":forms,
        "scripts":scripts[:100],
        "apiish":apiish[:200],
    }

def main():
    out=Path("output/delist_probe")
    out.mkdir(parents=True,exist_ok=True)
    report={}
    for name,url in URLS.items():
        text=fetch(url)
        (out/f"{name}.html").write_text(text,encoding="utf-8")
        report[name]=inspect(name,text)
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
