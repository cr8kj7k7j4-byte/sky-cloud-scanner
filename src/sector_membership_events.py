from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
import re
from typing import Iterable, Mapping


@dataclass(frozen=True)
class SectorChangeEvent:
    symbol: str
    exchange: str
    old_sector: str | None
    new_sector: str
    effective_date: str
    source_url: str = ""
    source_as_of: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _to_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


def parse_sector_change_text(
    text: str,
    *,
    exchange: str,
    source_url: str = "",
    source_as_of: str = "",
    effective_date: str | None = None,
) -> list[SectorChangeEvent]:
    """
    Parse official TWSE/TPEx announcement text of the form:
      股票代號：1595 ... 由「電子零組件業」調整為「半導體業」

    Only explicit old->new statements are returned. Group announcements that
    identify only the new category must be represented as boundary events with
    old_sector=None by a source-specific parser; old sectors are never guessed.
    """
    raw = text or ""

    if effective_date is None:
        # ROC dates like 115年6月1日 / 114年6月2日 / 112年7月3日
        m = re.search(
            r"(?:實施日期[:：]?|自)\s*(\d{2,3})年\s*(\d{1,2})月\s*(\d{1,2})日",
            raw,
        )
        if m:
            y, mo, d = map(int, m.groups())
            effective_date = f"{y + 1911:04d}-{mo:02d}-{d:02d}"

    if not effective_date:
        raise ValueError("effective_date not found")

    pattern = re.compile(
        r"(?:股票代號|證券代號)[:：]?\s*(\d{4}).{0,100}?"
        r"由[「\"]([^」\"]+)[」\"]\s*"
        r"(?:調整為|改為)[「\"]([^」\"]+)[」\"]",
        flags=re.S,
    )
    out = []
    for symbol, old_sector, new_sector in pattern.findall(raw):
        out.append(
            SectorChangeEvent(
                symbol=str(symbol),
                exchange=str(exchange),
                old_sector=old_sector.strip(),
                new_sector=new_sector.strip(),
                effective_date=str(effective_date),
                source_url=source_url,
                source_as_of=source_as_of,
            )
        )
    return out


def reconstruct_effective_sector_intervals(
    current_rows: Iterable[Mapping],
    change_events: Iterable[Mapping | SectorChangeEvent],
) -> dict:
    """
    Reconstruct historical effective-dated sector membership backwards from
    current official sector snapshots plus official change events.

    For a boundary event with old_sector=None, the post-change interval is
    preserved but reconstruction stops before the effective date and emits
    PRE_CHANGE_SECTOR_UNKNOWN. This is fail-closed and allows honest coverage
    measurement instead of discarding verified post-change evidence.
    """
    events_by_key: dict[tuple[str, str], list[SectorChangeEvent]] = {}
    for raw in change_events:
        ev = raw if isinstance(raw, SectorChangeEvent) else SectorChangeEvent(**dict(raw))
        events_by_key.setdefault((ev.symbol, ev.exchange), []).append(ev)

    intervals = []
    unresolved = []

    for row in current_rows:
        symbol = str(row.get("symbol") or "")
        exchange = str(row.get("exchange") or "")
        current_sector = str(row.get("sector") or "").strip()
        listed_from = row.get("listed_from")
        if not symbol or not exchange or not current_sector or not listed_from:
            unresolved.append({
                "symbol": symbol,
                "exchange": exchange,
                "reason": "MISSING_CURRENT_SNAPSHOT_FIELDS",
            })
            continue

        start_date = _to_date(listed_from)
        chain = sorted(
            events_by_key.get((symbol, exchange), []),
            key=lambda e: _to_date(e.effective_date),
            reverse=True,
        )

        sector = current_sector
        interval_end: date | None = None
        symbol_intervals = []
        valid = True
        stopped_on_unknown = False

        for ev in chain:
            eff = _to_date(ev.effective_date)
            if eff < start_date:
                continue
            if ev.new_sector != sector:
                unresolved.append({
                    "symbol": symbol,
                    "exchange": exchange,
                    "reason": "EVENT_CHAIN_NEW_SECTOR_MISMATCH",
                    "expected_current_sector": sector,
                    "event": ev.to_dict(),
                })
                valid = False
                break

            symbol_intervals.append({
                "symbol": symbol,
                "exchange": exchange,
                "name": str(row.get("name") or ""),
                "sector": sector,
                "effective_from": eff.isoformat(),
                "effective_to": interval_end.isoformat() if interval_end else None,
                "source": "official_sector_event_ledger",
                "source_url": ev.source_url,
                "source_as_of": ev.source_as_of or str(row.get("source_as_of") or ""),
            })
            interval_end = eff - timedelta(days=1)

            if not ev.old_sector:
                unresolved.append({
                    "symbol": symbol,
                    "exchange": exchange,
                    "reason": "PRE_CHANGE_SECTOR_UNKNOWN",
                    "unknown_from": start_date.isoformat(),
                    "unknown_to": interval_end.isoformat(),
                    "event": ev.to_dict(),
                })
                stopped_on_unknown = True
                break
            sector = ev.old_sector

        if not valid:
            continue

        if not stopped_on_unknown:
            symbol_intervals.append({
                "symbol": symbol,
                "exchange": exchange,
                "name": str(row.get("name") or ""),
                "sector": sector,
                "effective_from": start_date.isoformat(),
                "effective_to": interval_end.isoformat() if interval_end else None,
                "source": "official_sector_event_ledger",
                "source_url": str(row.get("source") or ""),
                "source_as_of": str(row.get("source_as_of") or ""),
            })
        intervals.extend(reversed(symbol_intervals))

    return {
        "schema_version": "1.1.0",
        "intervals": intervals,
        "unresolved": unresolved,
        "production_eligible": len(unresolved) == 0,
    }
