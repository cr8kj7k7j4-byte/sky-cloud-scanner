from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Iterable, Dict, List, Optional

PIT_UNIVERSE_SCHEMA_VERSION = "1.0.0"

def _date(v) -> date:
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    return datetime.fromisoformat(str(v)).date()

@dataclass(frozen=True)
class ListingInterval:
    symbol: str
    exchange: str
    name: str
    listed_from: str
    listed_to: Optional[str] = None
    source: str = "official"
    source_as_of: Optional[str] = None
    notes: str = ""

    def to_dict(self):
        return asdict(self)

    def contains(self, as_of) -> bool:
        d = _date(as_of)
        start = _date(self.listed_from)
        end = _date(self.listed_to) if self.listed_to else None
        return d >= start and (end is None or d <= end)

def validate_intervals(rows: Iterable[dict]) -> dict:
    errors = []
    by_symbol: Dict[str, List[ListingInterval]] = {}
    for i, raw in enumerate(rows or []):
        try:
            x = ListingInterval(**raw)
            start = _date(x.listed_from)
            end = _date(x.listed_to) if x.listed_to else None
            if end and end < start:
                errors.append(f"end_before_start:{i}:{x.symbol}")
            if not x.symbol or not x.exchange:
                errors.append(f"missing_identity:{i}")
            by_symbol.setdefault(x.symbol, []).append(x)
        except Exception as e:
            errors.append(f"invalid_row:{i}:{type(e).__name__}")

    for sym, arr in by_symbol.items():
        spans = sorted(arr, key=lambda z: _date(z.listed_from))
        for a, b in zip(spans, spans[1:]):
            a_end = _date(a.listed_to) if a.listed_to else date.max
            b_start = _date(b.listed_from)
            if b_start <= a_end:
                if a.exchange == b.exchange:
                    errors.append(f"overlap:{sym}:{a.exchange}")
                else:
                    errors.append(
                        f"cross_exchange_overlap:{sym}:{a.exchange}:{b.exchange}"
                    )

    return {
        "schema_version": PIT_UNIVERSE_SCHEMA_VERSION,
        "rows": sum(len(v) for v in by_symbol.values()),
        "symbols": len(by_symbol),
        "valid": not errors,
        "errors": errors,
    }

def universe_as_of(rows: Iterable[dict], as_of, exchanges=None) -> List[dict]:
    allowed = set(exchanges or [])
    out = []
    for raw in rows or []:
        x = ListingInterval(**raw)
        if allowed and x.exchange not in allowed:
            continue
        if x.contains(as_of):
            out.append({
                "symbol": x.symbol,
                "exchange": x.exchange,
                "name": x.name,
                "listed_from": x.listed_from,
                "listed_to": x.listed_to,
                "source": x.source,
            })
    out.sort(key=lambda z: (z["exchange"], z["symbol"]))
    return out

def membership_map(rows: Iterable[dict], dates: Iterable[str]) -> Dict[str, List[str]]:
    return {
        str(d): [x["symbol"] for x in universe_as_of(rows, d)]
        for d in dates
    }

def survivorship_audit(*, current_symbols: Iterable[str], pit_symbols: Iterable[str]) -> dict:
    current = set(current_symbols or [])
    pit = set(pit_symbols or [])
    missing_from_current = sorted(pit - current)
    not_yet_listed_at_date = sorted(current - pit)
    return {
        "current_n": len(current),
        "pit_n": len(pit),
        "historical_names_missing_from_current_universe": missing_from_current,
        "current_names_not_in_historical_universe": not_yet_listed_at_date,
        "survivorship_bias_present": bool(missing_from_current or not_yet_listed_at_date),
    }
