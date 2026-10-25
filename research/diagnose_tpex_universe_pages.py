from __future__ import annotations
import argparse,json,re
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

URLS={
 "TWSE_NEW":"https://www.twse.com.tw/company/newlisting?response=html",
 "TWSE_DELIST":"https://www.twse.com.tw/company/suspendListingCsvAndHtml?response=html",
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
    (outdir/f"{name.lower()}.html").write_text(html,encoding="utf-8")
    (outdir/f"{name.lower()}_inline.js").write_text(inline,encoding="utf-8")
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
    api_pattern_defs=[]
    for si,s in enumerate(scripts):
        try:
            sr=requests.get(s,timeout=20,headers={"User-Agent":"Mozilla/5.0"})
            txt=sr.text
            safe_name=re.sub(r"[^A-Za-z0-9._-]+","_",s.split("/")[-1] or f"script_{si}")
            if safe_name in {"main.js","tables.js"}:
                (outdir/f"{name.lower()}_{safe_name}").write_text(txt,encoding="utf-8")
            api_pattern_defs.extend(re.findall(r'API_PATTERN\s*=\s*([^;]+);',txt,re.I))
            hits=sorted(set(re.findall(r'[^"\'\s]{0,80}(?:api|ajax|query|delist|new-listed|mainboard)[^"\'\s]{0,120}',txt,re.I)))
            if hits:
                script_hits[s]=hits[:100]
        except Exception as e:
            script_hits[s]=[f"ERROR:{type(e).__name__}:{e}"]
    table_samples=[]
    for ti,table in enumerate(soup.find_all("table")[:5]):
        trs=table.find_all("tr")
        sample=[]
        for tr in trs[:6]:
            sample.append([x.get_text(" ",strip=True) for x in tr.find_all(["th","td"])])
        table_samples.append({"table_index":ti,"rows":sample})
    api_actions = sorted(set(re.findall(r'apiAction\s*[:=]\s*["\']([^"\']+)["\']', inline, re.I)))
    api_options = sorted(set(re.findall(r'apiOption\s*[:=]\s*["\']([^"\']+)["\']', inline, re.I)))
    action_attrs = sorted(set(re.findall(r'(?:data-)?api-action=["\']([^"\']+)["\']', html, re.I)))
    payload={
      "name":name,"url":url,"status":r.status_code,"content_type":r.headers.get("content-type"),
      "html_len":len(html),"tables":len(soup.find_all("table")),
      "scripts":scripts,"candidates":sorted(candidates)[:300],"script_hits":script_hits,
      "contains_6288":"6288" in html,
      "title":soup.title.get_text(" ",strip=True) if soup.title else None,
      "table_samples":table_samples,
      "body_prefix":soup.get_text("\n",strip=True)[:5000],
      "api_actions":api_actions,
      "api_options":api_options,
      "api_action_attributes":action_attrs,
      "api_pattern_defs":api_pattern_defs[:20],
      "inline_prefix":inline[:12000],
    }
    (outdir/f"{name.lower()}.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    return payload

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default="research_output_tpex_diag")
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    allp={}
    for name,url in URLS.items():
        allp[name]=diagnose(name,url,out)
    allp["TPEX_API_PROBES"] = probe_tpex_api(out)
    (out/"summary.json").write_text(json.dumps(allp,ensure_ascii=False,indent=2),encoding="utf-8")
    summary={}
    for k,v in allp.items():
        if k=="TPEX_API_PROBES":
            summary[k]={n:{
                "status":x.get("status"),
                "content_type":x.get("content_type"),
                "has_json":x.get("json") is not None,
                "error":x.get("error"),
            } for n,x in v.items()}
        else:
            summary[k]={
                "status":v.get("status"),"html_len":v.get("html_len"),"tables":v.get("tables"),
                "scripts":len(v.get("scripts",[])),"candidates":len(v.get("candidates",[])),
                "script_hit_files":len(v.get("script_hits",{}))
            }
    print(json.dumps(summary,ensure_ascii=False,indent=2))




def probe_tpex_api(outdir):
    endpoints = {
        "TPEX_NEW_API": (
            "https://www.tpex.org.tw/www/zh-tw/company/applicantStat",
            {"date": ""},
        ),
        "TPEX_DELIST_API": (
            "https://www.tpex.org.tw/www/zh-tw/company/deListed",
            {"code": "", "date": "", "reason": "-1"},
        ),
    }
    out = {}
    for name, (url, data) in endpoints.items():
        try:
            r = requests.post(
                url, data=data, timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://www.tpex.org.tw/zh-tw/",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
            rec = {
                "url": url,
                "status": r.status_code,
                "content_type": r.headers.get("content-type"),
                "text_prefix": r.text[:12000],
            }
            try:
                rec["json"] = r.json()
            except Exception:
                rec["json"] = None
            if name == "TPEX_NEW_API" and isinstance(rec.get("json"), dict):
                try:
                    tables = rec["json"].get("tables") or []
                    data_rows = tables[0].get("data") if tables else []
                    link = data_rows[0][1] if data_rows else None
                    if link:
                        dl_url = urljoin("https://www.tpex.org.tw", link)
                        dl = requests.get(dl_url, timeout=30, headers={"User-Agent":"Mozilla/5.0"})
                        rec["new_list_download_probe"] = {
                            "url": dl_url,
                            "status": dl.status_code,
                            "content_type": dl.headers.get("content-type"),
                            "content_disposition": dl.headers.get("content-disposition"),
                            "text_prefix": dl.text[:12000] if "text" in (dl.headers.get("content-type") or "") else None,
                            "bytes_prefix_hex": dl.content[:200].hex(),
                            "size_bytes": len(dl.content),
                        }
                except Exception as e:
                    rec["new_list_download_probe"] = {"error": f"{type(e).__name__}: {e}"}
            out[name] = rec
            (outdir/f"{name.lower()}.json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            out[name] = {"url": url, "error": f"{type(e).__name__}: {e}"}
    return out

if __name__=="__main__": main()
