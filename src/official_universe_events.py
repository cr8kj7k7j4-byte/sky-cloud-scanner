from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

TWSE_BASIC_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_BASIC_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
TWSE_NEW_URL = "https://www.twse.com.tw/rwd/zh/company/newlisting"
TWSE_DELIST_URL = "https://www.twse.com.tw/company/suspendListingCsvAndHtml?lang=zh&type=html"
TPEX_NEW_URL = "https://www.tpex.org.tw/www/zh-tw/company/applicantStatDl"
TPEX_DELIST_URL = "https://www.tpex.org.tw/www/zh-tw/company/deListed"

ROC_DATE_RE = re.compile(r"^\s*(\d{2,3})[./-](\d{1,2})[./-](\d{1,2})\s*$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

@dataclass(frozen=True)
class UniverseEvent:
    symbol: str
    exchange: str
    name: str
    event_type: str
    event_date: str
    source: str
    source_url: str
    source_as_of: str
    notes: str = ""

    def to_dict(self):
        return asdict(self)

def normalize_roc_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if ISO_DATE_RE.match(s):
        return s
    m = ROC_DATE_RE.match(s)
    if not m:
        digits = re.sub(r"\D", "", s)
        # 8-digit values from official basic data can be Gregorian YYYYMMDD
        # (e.g. 19960906). Do not add 1911 to those values.
        if len(digits) == 8:
            try:
                y = int(digits[:4])
                mo = int(digits[4:6])
                d = int(digits[6:8])
                if 1900 <= y <= 2100:
                    datetime(y, mo, d)
                    return f"{y:04d}-{mo:02d}-{d:02d}"
            except Exception:
                return None
        # Common ROC compact format: YYYMMDD, e.g. 1121215.
        if len(digits) == 7:
            try:
                y = int(digits[:3]) + 1911
                mo = int(digits[3:5])
                d = int(digits[5:7])
                datetime(y, mo, d)
                return f"{y:04d}-{mo:02d}-{d:02d}"
            except Exception:
                return None
        return None
    y, mo, d = map(int, m.groups())
    try:
        return f"{y+1911:04d}-{mo:02d}-{d:02d}"
    except Exception:
        return None

def _pick(row: Dict[str, Any], keys: Iterable[str]) -> Any:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return None

def _code(row):
    return str(_pick(row, ["公司代號","股票代號","證券代號","Code","SecuritiesCompanyCode"]) or "").strip()

def _name(row):
    return str(_pick(row, ["公司名稱","公司簡稱","證券名稱","Name","CompanyName"]) or "").strip()

def parse_basic_records(rows: Iterable[Dict[str, Any]], exchange: str, source_url: str, source_as_of: str) -> List[UniverseEvent]:
    out=[]
    date_keys = ["上市日期","股票上市買賣日期","上櫃日期","掛牌日期","ListingDate","DateOfListing"]
    for row in rows or []:
        symbol=_code(row)
        if not (len(symbol)==4 and symbol.isdigit()):
            continue
        listed=normalize_roc_date(_pick(row,date_keys))
        if not listed:
            continue
        out.append(UniverseEvent(
            symbol=symbol, exchange=exchange, name=_name(row),
            event_type="LIST", event_date=listed,
            source="official_basic_data", source_url=source_url,
            source_as_of=source_as_of
        ))
    return out

def _table_rows(html: str) -> List[Dict[str,str]]:
    soup=BeautifulSoup(html or "", "html.parser")
    rows=[]
    for table in soup.find_all("table"):
        trs=table.find_all("tr")
        if not trs:
            continue

        # Some official pages place a one-cell title row before the actual
        # column headers (e.g. TWSE delisting page). Pick the first row with
        # at least two cells as the header row.
        header_idx = None
        headers = []
        for i, tr in enumerate(trs):
            cells=[x.get_text(" ",strip=True) for x in tr.find_all(["th","td"])]
            if len(cells) >= 2:
                header_idx = i
                headers = cells
                break
        if header_idx is None or not headers:
            continue

        for tr in trs[header_idx+1:]:
            vals=[x.get_text(" ",strip=True) for x in tr.find_all(["th","td"])]
            if len(vals) != len(headers):
                continue
            rows.append(dict(zip(headers,vals)))
    return rows

def parse_listing_html(html: str, exchange: str, source_url: str, source_as_of: str) -> List[UniverseEvent]:
    out=[]
    for row in _table_rows(html):
        symbol=str(_pick(row,["公司代號","股票代號","證券代號","代號"]) or "").strip()
        if not (len(symbol)==4 and symbol.isdigit()):
            continue
        d=normalize_roc_date(_pick(row,["股票上市買賣日期","上櫃日期","開始買賣日期","掛牌日期"]))
        if not d:
            continue
        out.append(UniverseEvent(
            symbol=symbol,exchange=exchange,name=str(_pick(row,["公司簡稱","公司名稱","證券名稱","簡稱"]) or "").strip(),
            event_type="LIST",event_date=d,source="official_listing_page",source_url=source_url,
            source_as_of=source_as_of,notes=str(_pick(row,["備註","說明"]) or "").strip()
        ))
    return out

def parse_delisting_html(html: str, exchange: str, source_url: str, source_as_of: str) -> List[UniverseEvent]:
    out=[]
    for row in _table_rows(html):
        symbol=str(_pick(row,["上市編號","股票代號","證券代號","公司代號","代號"]) or "").strip()
        if not (len(symbol)==4 and symbol.isdigit()):
            continue
        d=normalize_roc_date(_pick(row,["終止上市日期","終止上櫃日期","終止買賣日期"]))
        if not d:
            continue
        out.append(UniverseEvent(
            symbol=symbol,exchange=exchange,name=str(_pick(row,["公司名稱","公司簡稱","證券名稱","簡稱"]) or "").strip(),
            event_type="DELIST",event_date=d,source="official_delisting_page",source_url=source_url,
            source_as_of=source_as_of,notes=str(_pick(row,["終止原因","原因","備註"]) or "").strip()
        ))
    return out

def parse_twse_newlisting_payload(payload: Dict[str, Any], source_url: str, source_as_of: str) -> List[UniverseEvent]:
    if not isinstance(payload, dict) or str(payload.get("stat") or "").upper() != "OK":
        return []
    fields=list(payload.get("fields") or [])
    data=list(payload.get("data") or [])
    if not fields or not data:
        return []
    out=[]
    for row in data:
        if not isinstance(row, list) or len(row) != len(fields):
            continue
        item=dict(zip(fields,row))
        symbol=str(item.get("公司代號") or "").strip()
        if not (len(symbol)==4 and symbol.isdigit()):
            continue
        d=normalize_roc_date(item.get("股票上市買賣日期"))
        if not d:
            continue
        out.append(UniverseEvent(
            symbol=symbol,
            exchange="TWSE",
            name=str(item.get("公司簡稱") or "").strip(),
            event_type="LIST",
            event_date=d,
            source="official_listing_api",
            source_url=source_url,
            source_as_of=source_as_of,
            notes=str(item.get("備註") or "").strip(),
        ))
    return out


def fetch_twse_newlisting_events(
    *,
    start_year: int = 2000,
    end_year: Optional[int] = None,
    timeout: int = 30,
    source_as_of: Optional[str] = None,
) -> List[UniverseEvent]:
    end_year=end_year or datetime.now().year
    source_as_of=source_as_of or datetime.now().astimezone().isoformat()
    events=[]
    for year in range(int(start_year), int(end_year)+1):
        r=requests.get(
            TWSE_NEW_URL,
            params={"date":str(year),"selectType":"","response":"json"},
            timeout=timeout,
            headers={"User-Agent":"sky-cloud-scanner/1.0"},
        )
        r.raise_for_status()
        events.extend(
            parse_twse_newlisting_payload(r.json(),TWSE_NEW_URL,source_as_of)
        )
    return dedupe_events(events)


def _decode_tpex_csv(raw: bytes) -> str:
    for enc in ("utf-8-sig","utf-8","cp950","big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("cp950",errors="replace")


def parse_tpex_newlisting_csv(text: str, source_url: str, source_as_of: str) -> List[UniverseEvent]:
    import csv
    from io import StringIO

    lines=(text or "").splitlines()
    if len(lines) < 2:
        return []
    # First line is a title; second line is the CSV header.
    reader=csv.DictReader(StringIO("\n".join(lines[1:])))
    out=[]
    for row in reader:
        symbol=str(row.get("公司代號") or "").strip()
        if not (len(symbol)==4 and symbol.isdigit()):
            continue
        d=normalize_roc_date(row.get("上櫃日期"))
        if not d:
            continue
        out.append(UniverseEvent(
            symbol=symbol,
            exchange="TPEx",
            name=str(row.get("公司名稱") or "").strip(),
            event_type="LIST",
            event_date=d,
            source="official_listing_csv",
            source_url=source_url,
            source_as_of=source_as_of,
        ))
    return out


def fetch_tpex_newlisting_events(
    *,
    start_year: int = 2005,
    end_year: Optional[int] = None,
    timeout: int = 30,
    source_as_of: Optional[str] = None,
) -> List[UniverseEvent]:
    end_year=end_year or datetime.now().year
    source_as_of=source_as_of or datetime.now().astimezone().isoformat()
    events=[]
    for year in range(int(start_year), int(end_year)+1):
        r=requests.get(
            TPEX_NEW_URL,
            params={"type":"list","date":str(year)},
            timeout=timeout,
            headers={
                "User-Agent":"sky-cloud-scanner/1.0",
                "Referer":"https://www.tpex.org.tw/zh-tw/mainboard/applying/status/new-listed.html",
            },
        )
        r.raise_for_status()
        ctype=str(r.headers.get("content-type") or "").lower()
        if "text/html" in ctype and "404" in r.text[:1000]:
            continue
        text=_decode_tpex_csv(r.content)
        events.extend(
            parse_tpex_newlisting_csv(text,TPEX_NEW_URL,source_as_of)
        )
    return dedupe_events(events)


def parse_tpex_delisting_payload(payload: Dict[str, Any], source_url: str, source_as_of: str) -> List[UniverseEvent]:
    if not isinstance(payload, dict) or payload.get("stat") != "ok":
        return []
    out=[]
    for table in payload.get("tables") or []:
        fields=list(table.get("fields") or [])
        data=list(table.get("data") or [])
        if not fields or not data:
            continue
        for row in data:
            if not isinstance(row, list) or len(row) != len(fields):
                continue
            item=dict(zip(fields,row))
            symbol=str(item.get("股票代號") or "").strip()
            if not (len(symbol)==4 and symbol.isdigit()):
                continue
            d=normalize_roc_date(item.get("終止上櫃日期"))
            if not d:
                continue
            out.append(UniverseEvent(
                symbol=symbol,
                exchange="TPEx",
                name=str(item.get("公司名稱") or "").strip(),
                event_type="DELIST",
                event_date=d,
                source="official_delisting_api",
                source_url=source_url,
                source_as_of=source_as_of,
                notes=str(item.get("終止上櫃原因") or "").strip(),
            ))
    return out


def fetch_tpex_delisting_events(
    *,
    start_year: int = 2021,
    end_year: Optional[int] = None,
    timeout: int = 30,
    source_as_of: Optional[str] = None,
) -> List[UniverseEvent]:
    end_year=end_year or datetime.now().year
    source_as_of=source_as_of or datetime.now().astimezone().isoformat()
    events=[]
    for year in range(int(start_year), int(end_year)+1):
        payload={
            "code":"",
            "date":str(year),
            "reason":"-1",
            "response":"json",
            "paging-offset":"0",
            "paging-size":"1000",
        }
        r=requests.post(
            TPEX_DELIST_URL,
            data=payload,
            timeout=timeout,
            headers={
                "User-Agent":"sky-cloud-scanner/1.0",
                "Referer":"https://www.tpex.org.tw/zh-tw/mainboard/listed/delisted.html",
                "Accept":"application/json,text/javascript,*/*;q=0.01",
                "X-Requested-With":"XMLHttpRequest",
            },
        )
        r.raise_for_status()
        events.extend(
            parse_tpex_delisting_payload(r.json(),TPEX_DELIST_URL,source_as_of)
        )
    return dedupe_events(events)


def fetch_json(url: str, timeout=30) -> Any:
    r=requests.get(url,timeout=timeout,headers={"User-Agent":"sky-cloud-scanner/1.0"})
    r.raise_for_status()
    return r.json()

def fetch_text(url: str, timeout=30) -> str:
    r=requests.get(url,timeout=timeout,headers={"User-Agent":"sky-cloud-scanner/1.0"})
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    return r.text

def dedupe_events(events: Iterable[UniverseEvent]) -> List[UniverseEvent]:
    seen={}
    for e in events:
        key=(e.symbol,e.exchange,e.event_type,e.event_date)
        if key not in seen:
            seen[key]=e
    return sorted(seen.values(),key=lambda e:(e.exchange,e.symbol,e.event_date,e.event_type))

def build_intervals(events: Iterable[UniverseEvent]) -> Dict[str, Any]:
    grouped={}
    for e in dedupe_events(events):
        grouped.setdefault((e.symbol,e.exchange),[]).append(e)
    intervals=[]
    unresolved=[]
    for (symbol,exchange), arr in grouped.items():
        lists=sorted([e for e in arr if e.event_type=="LIST"],key=lambda e:e.event_date)
        dels=sorted([e for e in arr if e.event_type=="DELIST"],key=lambda e:e.event_date)
        if not lists:
            for d in dels:
                unresolved.append({"symbol":symbol,"exchange":exchange,"reason":"DELIST_WITHOUT_CONFIRMED_LIST_DATE","event":d.to_dict()})
            continue
        for i,lst in enumerate(lists):
            next_list=lists[i+1].event_date if i+1<len(lists) else None
            eligible_dels=[d for d in dels if d.event_date>=lst.event_date and (next_list is None or d.event_date<next_list)]
            end=eligible_dels[0].event_date if eligible_dels else None
            intervals.append({
                "symbol":symbol,"exchange":exchange,"name":lst.name,
                "listed_from":lst.event_date,"listed_to":end,
                "source":"official_event_ledger",
                "source_as_of":max(e.source_as_of for e in arr if e.source_as_of),
                "notes":""
            })
    return {"intervals":intervals,"unresolved":unresolved}

def collect_official_events() -> Dict[str, Any]:
    as_of=datetime.now().astimezone().isoformat()
    events=[]
    health=[]
    sources=[
        ("TWSE_BASIC",TWSE_BASIC_URL,"json","TWSE","basic"),
        ("TPEX_BASIC",TPEX_BASIC_URL,"json","TPEx","basic"),
        ("TWSE_NEW",TWSE_NEW_URL,"custom","TWSE","list"),
        ("TWSE_DELIST",TWSE_DELIST_URL,"html","TWSE","delist"),
        ("TPEX_NEW",TPEX_NEW_URL,"custom","TPEx","list"),
        ("TPEX_DELIST",TPEX_DELIST_URL,"custom","TPEx","delist"),
    ]
    for name,url,kind,exchange,parser in sources:
        try:
            if kind=="json":
                payload=fetch_json(url)
                parsed=parse_basic_records(payload if isinstance(payload,list) else [],exchange,url,as_of)
            elif kind=="custom" and name=="TWSE_NEW":
                parsed=fetch_twse_newlisting_events(
                    start_year=2000,
                    end_year=datetime.now().year,
                    source_as_of=as_of,
                )
            elif kind=="custom" and name=="TPEX_NEW":
                parsed=fetch_tpex_newlisting_events(
                    start_year=2005,
                    end_year=datetime.now().year,
                    source_as_of=as_of,
                )
            elif kind=="custom" and name=="TPEX_DELIST":
                parsed=fetch_tpex_delisting_events(
                    start_year=2021,
                    end_year=datetime.now().year,
                    source_as_of=as_of,
                )
            else:
                html=fetch_text(url)
                parsed=parse_listing_html(html,exchange,url,as_of) if parser=="list" else parse_delisting_html(html,exchange,url,as_of)
            events.extend(parsed)
            health.append({"source":name,"url":url,"ok":True,"parsed_events":len(parsed)})
        except Exception as e:
            health.append({"source":name,"url":url,"ok":False,"parsed_events":0,"error":f"{type(e).__name__}: {e}"})
    events=dedupe_events(events)
    built=build_intervals(events)
    return {
        "schema_version":"1.0.0",
        "source_as_of":as_of,
        "health":health,
        "events":[e.to_dict() for e in events],
        **built,
        "production_eligible": all(x["ok"] for x in health) and not built["unresolved"],
        "note":"Fail closed: incomplete official source coverage or unresolved delisting events prevents production eligibility."
    }

def write_snapshot(path: str|Path, payload: Dict[str,Any]):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    return p
