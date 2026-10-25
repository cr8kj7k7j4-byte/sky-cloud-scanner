from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")


@dataclass(frozen=True)
class RevenueFilingTimestamp:
    symbol: str
    revenue_year: int
    revenue_month: int
    filing_published_at: str | None
    source: str
    source_url: str | None = None

    def to_dict(self):
        return asdict(self)


def normalize_mops_published_at(value: str | None, *, roc_year: int | None = None) -> str | None:
    """
    Normalize an official MOPS publication timestamp to Asia/Taipei ISO-8601.

    Accepted forms:
    - 115/10/21 17:43
    - 17:43, when roc_year/current date context is supplied by the caller later

    Time-only strings are intentionally rejected here because production PIT
    requires an unambiguous calendar date. Callers must first resolve the date
    from the official page/query context.
    """
    raw = str(value or "").strip()
    if not raw:
        return None

    for fmt in ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(raw, fmt).replace(tzinfo=TZ)
            return dt.isoformat()
        except ValueError:
            pass

    try:
        date_part, time_part = raw.split()
        ry, month, day = [int(x) for x in date_part.split("/")]
        if ry < 1911:
            year = ry + 1911
            dt = datetime.strptime(
                f"{year:04d}/{month:02d}/{day:02d} {time_part}",
                "%Y/%m/%d %H:%M",
            ).replace(tzinfo=TZ)
            return dt.isoformat()
    except Exception:
        return None

    return None


def revenue_pit_gate(record: dict) -> dict:
    filing = record.get("filing_published_at")
    source = str(record.get("filing_timestamp_source") or "").strip().upper()

    verified = bool(filing and source == "MOPS_OFFICIAL")
    return {
        "point_in_time_verified": verified,
        "filing_published_at": filing,
        "filing_timestamp_source": source or None,
        "promotion_allowed": verified,
        "reason": (
            "Official MOPS filing timestamp verified"
            if verified
            else "Missing official company-level MOPS filing timestamp"
        ),
    }
