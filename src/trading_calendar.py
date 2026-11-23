from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

TZ=ZoneInfo("Asia/Taipei")
TWSE_HOLIDAY_URL="https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule"

OPEN_MARKERS=("開始交易","最後交易")
CLOSED_MARKERS=("放假","市場無交易")


def _roc_to_iso(value: str) -> str | None:
    s=str(value or "").strip()
    if len(s)!=7 or not s.isdigit():
        return None
    year=int(s[:3])+1911
    return f"{year:04d}-{s[3:5]}-{s[5:7]}"


def classify_date(target: date, rows: list[dict]) -> dict:
    iso=target.isoformat()
    matches=[]
    for row in rows or []:
        d=_roc_to_iso(row.get("Date"))
        if d==iso:
            matches.append(dict(row))

    for row in matches:
        text=" ".join([
            str(row.get("Name") or ""),
            str(row.get("Description") or ""),
        ])
        if any(m in text for m in OPEN_MARKERS) and not any(
            m in text for m in CLOSED_MARKERS
        ):
            return {
                "date":iso,
                "market_open":True,
                "status":"OPEN_EXPLICIT",
                "matched":matches,
            }

    for row in matches:
        text=" ".join([
            str(row.get("Name") or ""),
            str(row.get("Description") or ""),
        ])
        if any(m in text for m in CLOSED_MARKERS):
            return {
                "date":iso,
                "market_open":False,
                "status":"CLOSED_OFFICIAL_SCHEDULE",
                "matched":matches,
            }

    if target.weekday()>=5:
        return {
            "date":iso,
            "market_open":False,
            "status":"CLOSED_WEEKEND",
            "matched":matches,
        }

    return {
        "date":iso,
        "market_open":True,
        "status":"OPEN_REGULAR_WEEKDAY",
        "matched":matches,
    }


def scheduled_scan_window(event_name: str, checked_at: datetime) -> dict:
    """Prevent delayed GitHub cron deliveries from spending paid API outside scan hours.

    The cron payload identifies a group of slots, not an exact individual slot.
    This guard is intentionally a conservative time window, not slot certification.
    Manual dispatch is unchanged; data-quality and trading-day gates still apply.
    """
    if not isinstance(checked_at, datetime) or checked_at.tzinfo is None:
        return {"allowed": False, "status": "HOLD_UNVERIFIED_CLOCK"}
    local = checked_at.astimezone(TZ)
    if event_name != "schedule":
        return {"allowed": True, "status": "NOT_SCHEDULED",
                "checked_at_tpe": local.isoformat()}
    first = datetime.combine(local.date(), time(9, 5), tzinfo=TZ)
    last = datetime.combine(local.date(), time(10, 25), tzinfo=TZ)
    allowed = first <= local <= last
    return {"allowed": allowed,
            "status": "WITHIN_SCHEDULED_SCAN_WINDOW" if allowed else "BLOCK_LATE_OR_EARLY_SCHEDULE",
            "checked_at_tpe": local.isoformat(),
            "window_start_tpe": first.isoformat(),
            "window_end_tpe": last.isoformat(),
            "note": "Bounded execution window only; not proof of any individual cron slot."}


def fetch_calendar(timeout: float=10.0) -> list[dict]:
    r=requests.get(TWSE_HOLIDAY_URL,timeout=timeout)
    r.raise_for_status()
    payload=r.json()
    if not isinstance(payload,list):
        raise ValueError("TWSE holiday payload is not a list")
    return [dict(x) for x in payload if isinstance(x,dict)]


def check_trading_day(target: date | None=None) -> dict:
    target=target or datetime.now(TZ).date()
    try:
        rows=fetch_calendar()
        result=classify_date(target,rows)
        result["source"]=TWSE_HOLIDAY_URL
        result["source_status"]="PASS"
        result["should_scan"]=bool(result["market_open"])
        result["fail_open"]=False
        return result
    except Exception as exc:
        # Calendar unavailability must not silently suppress a real trading day.
        # Fall back to weekday semantics and preserve the source failure.
        weekday_open=target.weekday()<5
        return {
            "date":target.isoformat(),
            "market_open":weekday_open,
            "should_scan":weekday_open,
            "status":"CALENDAR_SOURCE_ERROR_FALLBACK_WEEKDAY",
            "source":TWSE_HOLIDAY_URL,
            "source_status":"WARN",
            "fail_open":True,
            "error":f"{type(exc).__name__}: {exc}",
            "matched":[],
        }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--out",default="output/trading_calendar_status.json")
    args=ap.parse_args()

    target=(
        date.fromisoformat(args.date)
        if args.date
        else datetime.now(TZ).date()
    )
    result=check_trading_day(target)
    p=Path(args.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))


if __name__=="__main__":
    main()
