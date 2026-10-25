from __future__ import annotations

import json
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path

URLS = {
    "TWSE_NEW": "https://www.twse.com.tw/zh/listed/listed/new-listing.html",
    "TPEX_NEW": "https://www.tpex.org.tw/zh-tw/mainboard/applying/status/new-listed.html",
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
        trs=t.find_all("tr")
        rows=[]
        for tr in trs[:8]:
            rows.append([x.get_text(" ",strip=True) for x in tr.find_all(["th","td"])])
        tables.append({"index":i,"rows":len(trs),"sample_rows":rows})
    forms=[]
    for i,f in enumerate(soup.find_all("form")):
        forms.append({
            "index":i,
            "action":f.get("action"),
            "method":f.get("method"),
            "inputs":[
                {"name":x.get("name"),"id":x.get("id"),"type":x.get("type"),"value":x.get("value")}
                for x in f.find_all(["input","select","button"])[:100]
            ],
        })
    scripts=[x.get("src") for x in soup.find_all("script") if x.get("src")]
    inline="\n".join(x.get_text("\n",strip=False) for x in soup.find_all("script") if not x.get("src"))
    return {
        "name":name,
        "size":len(text),
        "tables":tables,
        "forms":forms,
        "scripts":scripts[:100],
        "inline_api_snippets":[
            inline[max(0,m.start()-400):m.start()+1200]
            for m in list(re.finditer(r"tables\.init|action:|new.?list|listing",inline,re.I))[:50]
        ],
    }

def main():
    out=Path("output/new_listing_probe")
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
