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
CLOSED_MARKERS=("放假","補假","市場無交易")


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
    Manual or push-triggered paid scans must remain inside TWSE intraday hours.
    Data-quality and trading-day gates remain independent and fail closed.
    """
    if not isinstance(checked_at, datetime) or checked_at.tzinfo is None:
        return {"allowed": False, "status": "HOLD_UNVERIFIED_CLOCK"}
    local = checked_at.astimezone(TZ)
    if event_name not in {"schedule", "workflow_dispatch", "push"}:
        return {"allowed": False, "status": "BLOCK_UNRECOGNIZED_SCAN_EVENT",
                "checked_at_tpe": local.isoformat()}
    scheduled = event_name == "schedule"
    first = datetime.combine(local.date(), time(9, 5) if scheduled else time(9, 0), tzinfo=TZ)
    last = datetime.combine(local.date(), time(10, 25) if scheduled else time(13, 30), tzinfo=TZ)
    allowed = first <= local <= last
    return {"allowed": allowed,
            "status": ("WITHIN_SCHEDULED_SCAN_WINDOW" if scheduled else "WITHIN_MANUAL_INTRADAY_WINDOW")
                      if allowed else ("BLOCK_LATE_OR_EARLY_SCHEDULE" if scheduled
                                      else "BLOCK_OUTSIDE_MANUAL_INTRADAY_WINDOW"),
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
    # A successful HTTP status is not evidence if the official payload is
    # empty or contains no usable schedule records.  Never certify a weekday
    # from an unverified empty response.
    rows = [dict(x) for x in payload if isinstance(x,dict)]
    if not rows:
        raise ValueError("TWSE_HOLIDAY_EMPTY_OR_INVALID_PAYLOAD")
    return rows


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
        # An unknown official trading day must NEVER release the paid API gate.
        # A weekday is not evidence that TWSE is open (holiday/makeup closure).
        # Keep the upstream failure visible for W0 diagnosis, not as a PASS.
        return {
            "date":target.isoformat(),
            "market_open":False,
            "should_scan":False,
            "status":"HOLD_OFFICIAL_CALENDAR_UNAVAILABLE",
            "source":TWSE_HOLIDAY_URL,
            "source_status":"HOLD",
            "fail_open":False,
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
