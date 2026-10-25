from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, time
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")

@dataclass(frozen=True)
class TradingSession:
    session_date: str
    market: str
    is_trading_day: bool
    open_time: Optional[str]
    close_time: Optional[str]
    source: str
    source_as_of: str
    note: str = ""

    def to_dict(self):
        return asdict(self)

def build_session(
    session_date,
    *,
    market="TW",
    is_trading_day,
    source,
    source_as_of,
    open_time="09:00:00",
    close_time="13:30:00",
    note="",
):
    d = str(session_date)
    return TradingSession(
        session_date=d,
        market=market,
        is_trading_day=bool(is_trading_day),
        open_time=open_time if is_trading_day else None,
        close_time=close_time if is_trading_day else None,
        source=str(source),
        source_as_of=str(source_as_of),
        note=str(note or ""),
    )

def validate_calendar(sessions: Iterable[TradingSession]):
    rows=list(sessions or [])
    errors=[]
    seen=set()
    for i,s in enumerate(rows):
        try:
            date.fromisoformat(s.session_date)
        except Exception:
            errors.append(f"invalid_date:{i}")
        if s.session_date in seen:
            errors.append(f"duplicate_date:{s.session_date}")
        seen.add(s.session_date)
        if not s.source or not s.source_as_of:
            errors.append(f"missing_provenance:{i}")
        if s.is_trading_day and (not s.open_time or not s.close_time):
            errors.append(f"missing_session_hours:{i}")
    return {"valid":not errors,"errors":errors,"rows":len(rows)}

def is_market_open(now: datetime, sessions: Iterable[TradingSession]):
    if now.tzinfo is None:
        now=now.replace(tzinfo=TZ)
    local=now.astimezone(TZ)
    session=next((s for s in sessions if s.session_date==local.date().isoformat()),None)
    if not session or not session.is_trading_day:
        return False
    o=time.fromisoformat(session.open_time)
    c=time.fromisoformat(session.close_time)
    return o <= local.time().replace(tzinfo=None) <= c
