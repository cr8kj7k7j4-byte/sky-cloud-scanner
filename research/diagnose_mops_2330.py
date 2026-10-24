from __future__ import annotations
import json, requests
from bs4 import BeautifulSoup
URL="https://mops.twse.com.tw/mops/web/t05st01"
params={"co_id":"2330","firstin":"1","step":"1","year":"115","TYPEK":"all","encodeURIComponent":"1"}
headers={"User-Agent":"Mozilla/5.0 SkyResearch/1.0","Referer":"https://mops.twse.com.tw/mops/web/t05st01"}
r=requests.get(URL,params=params,headers=headers,timeout=45)
open("mops_2330_115.html","w",encoding="utf-8").write(r.text)
s=BeautifulSoup(r.text,"html.parser")
tables=[]
for i,t in enumerate(s.find_all("table")[:20]):
    rows=[]
    for tr in t.find_all("tr")[:10]:
        rows.append([x.get_text(" ",strip=True) for x in tr.find_all(["th","td"])])
    tables.append({"i":i,"attrs":dict(t.attrs),"rows":rows})
inputs=[{"name":x.get("name"),"value":x.get("value"),"type":x.get("type")} for x in s.find_all("input")[:100]]
meta={"status":r.status_code,"url":r.url,"content_type":r.headers.get("content-type"),
      "length":len(r.text),"title":s.title.get_text(strip=True) if s.title else None,
      "tables":tables,"inputs":inputs,"text_head":s.get_text("\n",strip=True)[:5000]}
open("mops_2330_115_diag.json","w",encoding="utf-8").write(json.dumps(meta,ensure_ascii=False,indent=2))
print(json.dumps(meta,ensure_ascii=False,indent=2))
