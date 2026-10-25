from __future__ import annotations

import json
import requests
from pathlib import Path

URL="https://www.tpex.org.tw/www/zh-tw/company/deListed"

def main():
    payload={
        "code":"",
        "date":"",
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
    out=Path("output/tpex_delist_api")
    out.mkdir(parents=True,exist_ok=True)
    (out/"response.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    summary={
        "status_code":r.status_code,
        "top_keys":list(data.keys()) if isinstance(data,dict) else [],
        "stat":data.get("stat") if isinstance(data,dict) else None,
        "date":data.get("date") if isinstance(data,dict) else None,
        "tables":[],
    }
    for t in (data.get("tables") or []) if isinstance(data,dict) else []:
        summary["tables"].append({
            "fields":t.get("fields"),
            "rows":len(t.get("data") or []),
            "totalCount":t.get("totalCount"),
            "sample":(t.get("data") or [])[:5],
        })
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))

if __name__=="__main__":
    main()
