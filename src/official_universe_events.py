from __future__ import annotations

import csv
import io
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
TWSE_NEW_URL = "https://openapi.twse.com.tw/v1/company/newlisting"
TWSE_DELIST_URL = "https://openapi.twse.com.tw/v1/company/suspendListingCsvAndHtml"
TPEX_NEW_URL = "https://www.tpex.org.tw/zh-tw/mainboard/applying/status/new-listed.html"
TPEX_DELIST_URL = "https://www.tpex.org.tw/zh-tw/mainboard/listed/delisted.html"
TPEX_NEW_API = "https://www.tpex.org.tw/www/zh-tw/company/applicantStat"
TPEX_DELIST_API = "https://www.tpex.org.tw/www/zh-tw/company/deListed"

SOURCE_EXPECTATIONS = {
    "TWSE_BASIC": {"min_events": 100, "role": "CURRENT_BASE"},
    "TPEX_BASIC": {"min_events": 100, "role": "CURRENT_BASE"},
    "TWSE_NEW": {"min_events": 1, "role": "HISTORICAL_EVENT"},
    "TWSE_DELIST": {"min_events": 1, "role": "HISTORICAL_EVENT"},
    "TPEX_NEW": {"min_events": 1, "role": "HISTORICAL_EVENT"},
    "TPEX_DELIST": {"min_events": 1, "role": "HISTORICAL_EVENT"},
}

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
        try:
            # Gregorian compact date: YYYYMMDD
            if len(digits) == 8 and 1900 <= int(digits[:4]) <= 2100:
                y = int(digits[:4]); mo = int(digits[4:6]); d = int(digits[6:8])
                return f"{y:04d}-{mo:02d}-{d:02d}"
            # ROC compact date: YYYMMDD
            if len(digits) == 7:
                y = int(digits[:3]); mo = int(digits[3:5]); d = int(digits[5:7])
                return f"{y+1911:04d}-{mo:02d}-{d:02d}"
        except Exception:
            return None
        return None
    y, mo, d = map(int, m.groups())
    try:
        year = y if y >= 1900 else y + 1911
        if not (1900 <= year <= 2100):
            return None
        return f"{year:04d}-{mo:02d}-{d:02d}"
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


def parse_twse_new_records(rows: Iterable[Dict[str, Any]], source_url: str, source_as_of: str) -> List[UniverseEvent]:
    out=[]
    for row in rows or []:
        symbol=str(row.get("Code") or "").strip()
        if not (len(symbol)==4 and symbol.isdigit()):
            continue
        listed=normalize_roc_date(
            row.get("ApprovedListingDate") or row.get("ListingDate")
        )
        if not listed:
            continue
        out.append(UniverseEvent(
            symbol=symbol, exchange="TWSE", name=str(row.get("Company") or "").strip(),
            event_type="LIST", event_date=listed, source="TWSE_OPENAPI_NEWLISTING",
            source_url=source_url, source_as_of=source_as_of,
            notes=str(row.get("Note") or "").strip(),
        ))
    return out

def parse_twse_delist_records(rows: Iterable[Dict[str, Any]], source_url: str, source_as_of: str) -> List[UniverseEvent]:
    out=[]
    for row in rows or []:
        symbol=str(row.get("Code") or "").strip()
        if not (len(symbol)==4 and symbol.isdigit()):
            continue
        d=normalize_roc_date(row.get("DelistingDate"))
        if not d:
            continue
        out.append(UniverseEvent(
            symbol=symbol, exchange="TWSE", name=str(row.get("Company") or "").strip(),
            event_type="DELIST", event_date=d, source="TWSE_OPENAPI_DELIST",
            source_url=source_url, source_as_of=source_as_of,
        ))
    return out

def _table_rows(html: str) -> List[Dict[str,str]]:
    soup=BeautifulSoup(html or "", "html.parser")
    rows=[]
    for table in soup.find_all("table"):
        trs=table.find_all("tr")
        if not trs:
            continue
        headers=[x.get_text(" ",strip=True) for x in trs[0].find_all(["th","td"])]
        if not headers:
            continue
        for tr in trs[1:]:
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

def fetch_json(url: str, timeout=30) -> Any:
    r=requests.get(url,timeout=timeout,headers={"User-Agent":"sky-cloud-scanner/1.0"})
    r.raise_for_status()
    return r.json()

def fetch_text(url: str, timeout=30) -> str:
    r=requests.get(url,timeout=timeout,headers={"User-Agent":"sky-cloud-scanner/1.0"})
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    return r.text

def post_json(url: str, data: Dict[str, Any], timeout=30) -> Any:
    r=requests.post(
        url, data=data, timeout=timeout,
        headers={
            "User-Agent":"sky-cloud-scanner/1.0",
            "Referer":"https://www.tpex.org.tw/zh-tw/",
            "X-Requested-With":"XMLHttpRequest",
        },
    )
    r.raise_for_status()
    return r.json()

def _payload_table_dicts(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    tables = payload.get("tables") if isinstance(payload, dict) else None
    if not isinstance(tables, list) or not tables:
        return []
    table = tables[0] if isinstance(tables[0], dict) else {}
    fields = table.get("fields") or []
    data = table.get("data") or []
    out=[]
    if not isinstance(fields, list) or not isinstance(data, list):
        return out
    for row in data:
        if isinstance(row, list) and len(row) >= len(fields):
            out.append(dict(zip(fields,row)))
    return out

def fetch_tpex_new_events(source_as_of: str, start_year: int = 2005, end_year: Optional[int] = None) -> List[UniverseEvent]:
    end_year = end_year or datetime.now().year
    out=[]
    for year in range(int(start_year), int(end_year)+1):
        url=f"https://www.tpex.org.tw/www/zh-tw/company/applicantStatDl?type=list&date={year}"
        r=requests.get(url,timeout=30,headers={"User-Agent":"sky-cloud-scanner/1.0"})
        r.raise_for_status()
        text=r.content.decode("cp950",errors="replace")
        lines=text.splitlines()
        if len(lines) < 2:
            continue
        reader=csv.DictReader(io.StringIO("\n".join(lines[1:])))
        for row in reader:
            symbol=str(row.get("公司代號") or "").strip()
            if not (len(symbol)==4 and symbol.isdigit()):
                continue
            d=normalize_roc_date(row.get("上櫃日期"))
            if not d:
                continue
            out.append(UniverseEvent(
                symbol=symbol, exchange="TPEx",
                name=str(row.get("公司名稱") or "").strip(),
                event_type="LIST", event_date=d,
                source="TPEX_OFFICIAL_NEWLIST_CSV", source_url=url,
                source_as_of=source_as_of,
                notes=f"source_year={year}",
            ))
    return out

def fetch_tpex_delist_events(source_as_of: str, start_year: int = 2021, end_year: Optional[int] = None) -> List[UniverseEvent]:
    end_year = end_year or datetime.now().year
    out=[]
    for year in range(int(start_year), int(end_year)+1):
        payload=post_json(TPEX_DELIST_API, {"code":"","date":str(year),"reason":"-1"})
        for row in _payload_table_dicts(payload):
            symbol=str(row.get("股票代號") or "").strip()
            if not (len(symbol)==4 and symbol.isdigit()):
                continue
            d=normalize_roc_date(row.get("終止上櫃日期"))
            if not d:
                continue
            out.append(UniverseEvent(
                symbol=symbol, exchange="TPEx",
                name=str(row.get("公司名稱") or "").strip(),
                event_type="DELIST", event_date=d,
                source="TPEX_API_DELIST", source_url=TPEX_DELIST_API,
                source_as_of=source_as_of,
                notes=str(row.get("終止上櫃原因") or "").strip(),
            ))
    return out

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
    continuity_notes=[]
    for (symbol,exchange), arr in grouped.items():
        arr=sorted(arr,key=lambda e:(e.event_date, 0 if e.event_type=="LIST" else 1))
        active=None
        duplicate_lists=[]
        for e in arr:
            if e.event_type=="LIST":
                if active is None:
                    active=e
                    duplicate_lists=[]
                else:
                    # Same-exchange LIST without an intervening DELIST is a
                    # continuous membership/status transition, not a new interval.
                    duplicate_lists.append(e)
            elif e.event_type=="DELIST":
                if active is None:
                    unresolved.append({
                        "symbol":symbol,"exchange":exchange,
                        "reason":"DELIST_WITHOUT_CONFIRMED_LIST_DATE",
                        "event":e.to_dict()
                    })
                else:
                    intervals.append({
                        "symbol":symbol,"exchange":exchange,"name":active.name,
                        "listed_from":active.event_date,"listed_to":e.event_date,
                        "source":"official_event_ledger",
                        "source_as_of":max(x.source_as_of for x in arr if x.source_as_of),
                        "notes":(
                            f"continuous_list_events_ignored={len(duplicate_lists)}"
                            if duplicate_lists else ""
                        )
                    })
                    if duplicate_lists:
                        continuity_notes.append({
                            "symbol":symbol,"exchange":exchange,
                            "kept_list_date":active.event_date,
                            "ignored_list_dates":[x.event_date for x in duplicate_lists],
                        })
                    active=None
                    duplicate_lists=[]
        if active is not None:
            intervals.append({
                "symbol":symbol,"exchange":exchange,"name":active.name,
                "listed_from":active.event_date,"listed_to":None,
                "source":"official_event_ledger",
                "source_as_of":max(x.source_as_of for x in arr if x.source_as_of),
                "notes":(
                    f"continuous_list_events_ignored={len(duplicate_lists)}"
                    if duplicate_lists else ""
                )
            })
            if duplicate_lists:
                continuity_notes.append({
                    "symbol":symbol,"exchange":exchange,
                    "kept_list_date":active.event_date,
                    "ignored_list_dates":[x.event_date for x in duplicate_lists],
                })
    return {
        "intervals":intervals,
        "unresolved":unresolved,
        "continuity_notes":continuity_notes,
    }

def assess_source_health(name: str, parsed_events: int, *, transport_ok: bool, error: str | None = None) -> dict:
    expectation = SOURCE_EXPECTATIONS.get(name, {"min_events": 1, "role": "UNKNOWN"})
    min_events = int(expectation["min_events"])
    if not transport_ok:
        status = "TRANSPORT_FAIL"
        healthy = False
    elif int(parsed_events) < min_events:
        status = "PARSE_SUSPECT"
        healthy = False
    else:
        status = "OK"
        healthy = True
    out = {
        "source": name,
        "transport_ok": bool(transport_ok),
        "parse_status": status,
        "healthy": healthy,
        "parsed_events": int(parsed_events),
        "min_expected_events": min_events,
        "role": expectation["role"],
    }
    if error:
        out["error"] = error
    return out

def collect_official_events() -> Dict[str, Any]:
    as_of=datetime.now().astimezone().isoformat()
    events=[]
    health=[]
    sources=[
        ("TWSE_BASIC",TWSE_BASIC_URL,"json","TWSE","basic"),
        ("TPEX_BASIC",TPEX_BASIC_URL,"json","TPEx","basic"),
        ("TWSE_NEW",TWSE_NEW_URL,"json","TWSE","twse_new"),
        ("TWSE_DELIST",TWSE_DELIST_URL,"json","TWSE","twse_delist"),
        ("TPEX_NEW",TPEX_NEW_API,"tpex_new_api","TPEx","list"),
        ("TPEX_DELIST",TPEX_DELIST_API,"tpex_delist_api","TPEx","delist"),
    ]
    for name,url,kind,exchange,parser in sources:
        try:
            if kind=="json":
                payload=fetch_json(url)
                rows=payload if isinstance(payload,list) else []
                if parser=="twse_new":
                    parsed=parse_twse_new_records(rows,url,as_of)
                elif parser=="twse_delist":
                    parsed=parse_twse_delist_records(rows,url,as_of)
                else:
                    parsed=parse_basic_records(rows,exchange,url,as_of)
            elif kind=="tpex_new_api":
                parsed=fetch_tpex_new_events(as_of)
            elif kind=="tpex_delist_api":
                parsed=fetch_tpex_delist_events(as_of)
            else:
                html=fetch_text(url)
                parsed=parse_listing_html(html,exchange,url,as_of) if parser=="list" else parse_delisting_html(html,exchange,url,as_of)
            events.extend(parsed)
            h = assess_source_health(name, len(parsed), transport_ok=True)
            h["url"] = url
            health.append(h)
        except Exception as e:
            h = assess_source_health(
                name, 0, transport_ok=False,
                error=f"{type(e).__name__}: {e}"
            )
            h["url"] = url
            health.append(h)
    events=dedupe_events(events)
    built=build_intervals(events)
    return {
        "schema_version":"1.0.0",
        "source_as_of":as_of,
        "health":health,
        "events":[e.to_dict() for e in events],
        **built,
        "production_eligible": all(x["healthy"] for x in health) and not built["unresolved"],
        "source_health_complete": all(x["healthy"] for x in health),
        "note":"Fail closed: transport success alone is insufficient. Zero/implausibly low parsed event counts, incomplete historical coverage, or unresolved delisting events prevent production eligibility."
    }

def write_snapshot(path: str|Path, payload: Dict[str,Any]):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    return p
