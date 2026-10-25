from __future__ import annotations

import json
import requests
from pathlib import Path

URL="https://www.tpex.org.tw/www/zh-tw/company/deListed"

def main():
    out=Path("output/tpex_delist_api")
    out.mkdir(parents=True,exist_ok=True)
    summary={"years":{}}
    for year in (2023,2024,2025,2026):
        payload={
            "code":"",
            "date":str(year),
            "reason":"-1",
            "response":"json",
            "paging-offset":"0",
            "paging-size":"1000",
        }
        r=requests.post(
            URL,
            data=payload,
            timeout=30,
            headers={
                "User-Agent":"Mozilla/5.0 SkyResearchBot/1.0",
                "Referer":"https://www.tpex.org.tw/zh-tw/mainboard/listed/delisted.html",
                "Accept":"application/json,text/javascript,*/*;q=0.01",
                "X-Requested-With":"XMLHttpRequest",
            },
        )
        r.raise_for_status()
        data=r.json()
        (out/f"response_{year}.json").write_text(
            json.dumps(data,ensure_ascii=False,indent=2),
            encoding="utf-8",
        )
        tables=[]
        for t in (data.get("tables") or []) if isinstance(data,dict) else []:
            tables.append({
                "fields":t.get("fields"),
                "rows":len(t.get("data") or []),
                "totalCount":t.get("totalCount"),
                "sample":(t.get("data") or [])[:3],
            })
        summary["years"][str(year)]={
            "status_code":r.status_code,
            "stat":data.get("stat"),
            "date":data.get("date"),
            "tables":tables,
        }
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))

if __name__=="__main__":
    main()
