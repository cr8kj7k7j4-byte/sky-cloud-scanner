"""Research-only audit of official PIT corporate actions.

Never activate an adjusted daily-price series from this audit alone.
Official event dates on a verified exchange closure or capital reduction
require manual authoritative effective-date / suspension reconciliation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from research.collect_swing_official_daily_delta import SYMBOL, value, join_pit


def normalize_roc_day(raw: str) -> str:
    s=str(raw or "").strip()
    s=s.replace("年","/").replace("月","/").replace("日","")
    s=re.sub(r"\s+","",s)
    parts=s.split("/")
    if len(parts)==3:
        y,m,d=[int(t) for t in parts]
    else:
        s=s.replace("/","")
        if len(s)!=7 or not s.isdigit():
            raise ValueError(f"invalid ROC date {raw!r}")
        y,m,d=int(s[:3]),int(s[3:5]),int(s[5:7])
    from datetime import date
    return date(y+1911,m,d).isoformat()


def _rows(payload: dict, key: str) -> list[dict]:
    if key=="TWSE_EXRIGHT_ALT_START":
        if str(payload.get("strDate"))!="20261023" or str(payload.get("endDate"))!="20261104" or payload.get("stat")!="OK":
            raise ValueError("TWSE official CA source date range not certified")
        fields=payload.get("fields") or []
        data=payload.get("data") or []
        market="TWSE"
        kind="EXRIGHT"
    else:
        if str(payload.get("date"))!="20261023~20261104" or str(payload.get("stat")).lower()!="ok":
            raise ValueError(f"{key}: official CA source date range not certified")
        tables=payload.get("tables") or []
        if len(tables)!=1:
            raise ValueError(f"{key}: expected exactly one data table")
        fields=tables[0].get("fields") or []
        data=tables[0].get("data") or []
        market="TPEx"
        kind="CAPITAL_REDUCTION" if key=="TPEX_CAPITAL_REDUCTION_RESUME" else "EXRIGHT"
    col={str(x).strip():i for i,x in enumerate(fields)}
    def field(row,name):
        i=col[name]
        return row[i] if i<len(row) else None
    out=[]
    for row in data:
        symbol=str(field(row,"股票代號" if kind=="CAPITAL_REDUCTION" or market=="TWSE" else "代號") or "").strip()
        if not SYMBOL.fullmatch(symbol):
            continue
        raw_date=field(row,"恢復買賣日期") if kind=="CAPITAL_REDUCTION" else field(row,"資料日期" if market=="TWSE" else "除權息日期")
        day=normalize_roc_day(raw_date)
        if kind=="CAPITAL_REDUCTION":
            before=value(field(row,"最後交易日之收盤價格"))
            reference=value(field(row,"減資恢復買賣開始日參考價格"))
            description=str(field(row,"減資原因") or "")
        elif market=="TWSE":
            before=value(field(row,"除權息前收盤價"))
            reference=value(field(row,"除權息參考價"))
            description=str(field(row,"權/息") or "")
        else:
            before=value(field(row,"除權息前收盤價"))
            reference=value(field(row,"除權息參考價"))
            description=str(field(row,"權/息") or "")
        if before is None or reference is None or before<=0 or reference<=0:
            raise ValueError(f"{key} {symbol} {day}: missing official prices")
        ratio=reference/before
        if not 0.1 < ratio < 10:
            raise ValueError(f"{key} {symbol} {day}: implausible event factor")
        out.append({
            "symbol":symbol,"exchange":market,"date":day,
            "event_kind":kind,"description":description,
            "official_pre_close":before,"official_reference_price":reference,
            "candidate_backward_price_ratio":ratio,
            "source":key,"source_date_range_verified":True,
        })
    return out


def build_candidate_ledger(source_dir: Path,backfill_audit: dict,pit:dict)->dict:
    sources=("TWSE_EXRIGHT_ALT_START","TPEX_EXRIGHT_REFERENCE","TPEX_CAPITAL_REDUCTION_RESUME")
    events=[]
    for key in sources:
        payload=json.loads((source_dir/f"{key}.json").read_text(encoding="utf-8"))
        events.extend(_rows(payload,key))
    closed={x["date"] for x in backfill_audit.get("closed_days") or []}
    intervals=pit.get("intervals") or []
    seen=set()
    reported=[]
    for e in events:
        k=(e["exchange"],e["symbol"],e["date"],e["event_kind"])
        if k in seen:
            raise ValueError(f"duplicate event: {k}")
        seen.add(k)
        matched,unmatched=join_pit([{"symbol":e["symbol"],"exchange":e["exchange"],"date":e["date"]}],intervals)
        reasons=[]
        if e["date"] in closed:
            reasons.append("EVENT_DATE_MARKED_EXCHANGE_CLOSED")
        if len(matched)!=1 or unmatched:
            reasons.append("PIT_IDENTITY_NOT_UNAMBIGUOUS")
        if e["event_kind"]=="CAPITAL_REDUCTION":
            reasons.append("CAPITAL_REDUCTION_SUSPENSION_AND_RATIO_RECONCILIATION_REQUIRED")
        if "權" in e["description"] or e["event_kind"]=="CAPITAL_REDUCTION":
            reasons.append("STRUCTURAL_OR_COMPLEX_ACTION_MANUAL_REVIEW")
        if not reasons:
            reasons.append("ASOF_SOURCE_EVENT_LEDGER_APPEND_NOT_YET_VERIFIED")
        reported.append({**e,"apply_to_history":False,"review_reasons":reasons})
    return {
        "schema_version":"SKY_SWING_CA_CANDIDATE_LEDGER_1",
        "status":"CORPORATE_ACTION_RECONCILIATION_HOLD",
        "period":["2026-10-23","2026-11-04"],
        "count":len(reported),
        "exchange_closed_date_events":sum("EVENT_DATE_MARKED_EXCHANGE_CLOSED" in e["review_reasons"] for e in reported),
        "capital_reduction_events":sum(e["event_kind"]=="CAPITAL_REDUCTION" for e in reported),
        "production_eligible":False,
        "w1_v11_signal_eligible":False,
        "all_price_adjustment_factors_applied":False,
        "missing_source_families":["TWSE capital reductions","TWSE/TPEx face-value changes and non-dividend stock splits"],
        "events":reported,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-dir",required=True)
    ap.add_argument("--backfill-audit",required=True)
    ap.add_argument("--pit-json",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    doc=build_candidate_ledger(
        Path(args.source_dir),
        json.loads(Path(args.backfill_audit).read_text(encoding="utf-8")),
        json.loads(Path(args.pit_json).read_text(encoding="utf-8")),
    )
    out.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({
        "status":doc["status"],
        "count":doc["count"],
        "closed_date_events":doc["exchange_closed_date_events"],
        "capital_reduction_events":doc["capital_reduction_events"],
        "sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
    },ensure_ascii=False))


if __name__=="__main__":
    main()
