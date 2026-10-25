from __future__ import annotations
import argparse,json,re
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

URLS={
 "TPEX_NEW":"https://www.tpex.org.tw/zh-tw/mainboard/applying/status/new-listed.html",
 "TPEX_DELIST":"https://www.tpex.org.tw/zh-tw/mainboard/listed/delisted.html",
}

PATTERNS=[
 r'https?://[^"\'\s<>]+',
 r'/(?:api|web|service|ajax|openapi|mainboard)[^"\'\s<>]+',
 r'fetch\(([^)]+)\)',
 r'ajax\s*:\s*[^,}]+',
 r'url\s*:\s*["\']([^"\']+)["\']',
]

def diagnose(name,url,outdir):
    r=requests.get(url,timeout=30,headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    html=r.text
    soup=BeautifulSoup(html,"html.parser")
    scripts=[urljoin(url,x.get("src")) for x in soup.find_all("script") if x.get("src")]
    inline="\n".join(x.get_text("\n") for x in soup.find_all("script") if not x.get("src"))
    candidates=set()
    for text in (html,inline):
        for pat in PATTERNS:
            try:
                for m in re.findall(pat,text,re.I):
                    if isinstance(m,tuple): m="".join(m)
                    s=str(m).strip().strip('"\'')
                    if s:
                        candidates.add(urljoin(url,s))
            except re.error:
                pass
    script_hits={}
    for s in scripts:
        try:
            sr=requests.get(s,timeout=20,headers={"User-Agent":"Mozilla/5.0"})
            txt=sr.text
            hits=sorted(set(re.findall(r'[^"\'\s]{0,80}(?:api|ajax|query|delist|new-listed|mainboard)[^"\'\s]{0,120}',txt,re.I)))
            if hits:
                script_hits[s]=hits[:100]
        except Exception as e:
            script_hits[s]=[f"ERROR:{type(e).__name__}:{e}"]
    payload={
      "name":name,"url":url,"status":r.status_code,"content_type":r.headers.get("content-type"),
      "html_len":len(html),"tables":len(soup.find_all("table")),
      "scripts":scripts,"candidates":sorted(candidates)[:300],"script_hits":script_hits,
      "contains_6288":"6288" in html,
      "title":soup.title.get_text(" ",strip=True) if soup.title else None,
    }
    (outdir/f"{name.lower()}.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    return payload

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default="research_output_tpex_diag")
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    allp={}
    for name,url in URLS.items():
        allp[name]=diagnose(name,url,out)
    (out/"summary.json").write_text(json.dumps(allp,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:{
      "status":v["status"],"html_len":v["html_len"],"tables":v["tables"],
      "scripts":len(v["scripts"]),"candidates":len(v["candidates"]),"script_hit_files":len(v["script_hits"])
    } for k,v in allp.items()},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
