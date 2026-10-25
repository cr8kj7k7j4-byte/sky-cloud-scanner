from __future__ import annotations

import json
import requests
from pathlib import Path

TWSE="https://www.twse.com.tw/rwd/zh/company/newlisting"
TPEX="https://www.tpex.org.tw/www/zh-tw/company/applicantStat"

def summarize(data):
    out={"top_keys":list(data.keys()) if isinstance(data,dict) else []}
    if isinstance(data,dict):
        out["stat"]=data.get("stat")
        out["date"]=data.get("date")
        out["fields"]=data.get("fields")
        out["rows"]=len(data.get("data") or [])
        out["sample"]=(data.get("data") or [])[:3]
        out["tables"]=[]
        for t in data.get("tables") or []:
            out["tables"].append({
                "fields":t.get("fields"),
                "rows":len(t.get("data") or []),
                "totalCount":t.get("totalCount"),
                "sample":(t.get("data") or [])[:3],
            })
    return out

def main():
    out=Path("output/new_listing_api_probe")
    out.mkdir(parents=True,exist_ok=True)
    report={"twse":{},"tpex":{}}
    for year in (2023,2024,2025,2026):
        r=requests.get(
            TWSE,
            params={"date":str(year),"selectType":"","response":"json"},
            timeout=30,
            headers={"User-Agent":"Mozilla/5.0 SkyResearchBot/1.0"},
        )
        r.raise_for_status()
        data=r.json()
        (out/f"twse_{year}.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        report["twse"][str(year)]=summarize(data)

        r=requests.post(
            TPEX,
            data={"date":str(year),"response":"json"},
            timeout=30,
            headers={
                "User-Agent":"Mozilla/5.0 SkyResearchBot/1.0",
                "Referer":"https://www.tpex.org.tw/zh-tw/mainboard/applying/status/new-listed.html",
                "Accept":"application/json,text/javascript,*/*;q=0.01",
                "X-Requested-With":"XMLHttpRequest",
            },
        )
        r.raise_for_status()
        data=r.json()
        (out/f"tpex_{year}.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        report["tpex"][str(year)]=summarize(data)

    (out/"summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
