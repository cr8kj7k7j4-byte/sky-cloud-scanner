from __future__ import annotations

import html
import json
import re
import urllib.request
from pathlib import Path

API = "https://mops.twse.com.tw/mops/api/home_page/t51sb10"

def post_json(url, payload, timeout=20):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "User-Agent":"Mozilla/5.0 SkyResearchBot/1.0",
            "Content-Type":"application/json",
            "Accept-Language":"zh-TW,zh;q=0.9",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def get_text(url, timeout=20):
    req=urllib.request.Request(
        url,
        headers={
            "User-Agent":"Mozilla/5.0 SkyResearchBot/1.0",
            "Accept-Language":"zh-TW,zh;q=0.9",
            "Referer":"https://mops.twse.com.tw/mops/",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw=r.read()
    for enc in ("utf-8","big5","cp950"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8",errors="ignore")

def extract_form_metadata(text):
    forms=[]
    for m in re.finditer(r"<form\b([^>]*)>(.*?)</form>",text,re.I|re.S):
        attrs=m.group(1)
        body=m.group(2)
        action=re.search(r'action=["\']([^"\']*)',attrs,re.I)
        method=re.search(r'method=["\']([^"\']*)',attrs,re.I)
        names=sorted(set(re.findall(r'name=["\']([^"\']+)',body,re.I)))
        ids=sorted(set(re.findall(r'id=["\']([^"\']+)',body,re.I)))
        forms.append({
            "action": html.unescape(action.group(1)) if action else None,
            "method": method.group(1).upper() if method else None,
            "names": names,
            "ids": ids,
        })
    return forms

def main():
    out=Path("output/mops_backfill_moreinfo")
    out.mkdir(parents=True,exist_ok=True)
    report={"markets":{}}
    for market in ("sii","otc","rotc","pub"):
        payload=post_json(API,{"count":3,"marketKind":market})
        url=((payload.get("result") or {}).get("moreInfoUrl"))
        item={
            "api_code":payload.get("code"),
            "api_message":payload.get("message"),
            "api_datetime":payload.get("datetime"),
            "moreInfoUrl":url,
        }
        if url:
            try:
                text=get_text(url)
                (out/f"{market}.html").write_text(text,encoding="utf-8")
                item["html_size"]=len(text)
                item["forms"]=extract_form_metadata(text)
                item["year_tokens"]=sorted(set(re.findall(r"\b(?:year|yy|yyy|yymm|month|mm|date|startDate|endDate|queryDate)\b",text,re.I)))
                item["urls"]=sorted(set(re.findall(r'https?://[^"\'<> ]+',text)))[:50]
                item["ajax_names"]=sorted(set(re.findall(r"ajax_[A-Za-z0-9_]+",text)))
            except Exception as exc:
                item["exception"]=f"{type(exc).__name__}: {exc}"
        report["markets"][market]=item

    (out/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
