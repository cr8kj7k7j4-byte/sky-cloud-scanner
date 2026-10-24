from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping


@dataclass(frozen=True)
class VWAPEntryRecord:
    symbol: str
    as_of: str
    entry_price: float
    vwap: float
    price_vs_vwap_pct: float
    session_low: float | None
    session_high: float | None
    session_position: float | None
    rvol: float | None
    spread_pct: float | None

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "as_of": self.as_of,
            "entry_price": self.entry_price,
            "vwap": self.vwap,
            "price_vs_vwap_pct": self.price_vs_vwap_pct,
            "session_low": self.session_low,
            "session_high": self.session_high,
            "session_position": self.session_position,
            "rvol": self.rvol,
            "spread_pct": self.spread_pct,
        }


def _iso(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _session_position(price: float, low: float | None, high: float | None) -> float | None:
    if low is None or high is None:
        return None
    low = float(low)
    high = float(high)
    if high <= low:
        return None
    return (float(price) - low) / (high - low)


def build_vwap_entry_records(rows: Iterable[Mapping]) -> list[VWAPEntryRecord]:
    """
    Build point-in-time VWAP / entry-location features.

    Required fields:
      symbol, as_of, entry_price, vwap

    Optional fields:
      session_low, session_high, rvol, spread_pct

    This function must receive values frozen at decision/entry time.
    It must never derive VWAP or entry-location features from exit data,
    later bars, MFE/MAE, or realized trade outcomes.
    """
    out = []
    for row in rows:
        entry = row.get("entry_price")
        vwap = row.get("vwap")
        if entry is None or vwap in (None, 0):
            continue

        entry = float(entry)
        vwap = float(vwap)
        low = row.get("session_low")
        high = row.get("session_high")

        out.append(
            VWAPEntryRecord(
                symbol=str(row["symbol"]),
                as_of=_iso(row["as_of"]),
                entry_price=entry,
                vwap=vwap,
                price_vs_vwap_pct=(entry - vwap) / vwap,
                session_low=float(low) if low is not None else None,
                session_high=float(high) if high is not None else None,
                session_position=_session_position(entry, low, high),
                rvol=float(row["rvol"]) if row.get("rvol") is not None else None,
                spread_pct=float(row["spread_pct"]) if row.get("spread_pct") is not None else None,
            )
        )
    return out


def attach_vwap_entry_to_trades(
    trades: Iterable[Mapping],
    records: Iterable[VWAPEntryRecord],
) -> list[dict]:
    lookup = {(r.symbol, r.as_of[:10]): r for r in records}
    enriched = []

    for trade in trades:
        x = dict(trade)
        symbol = str(x.get("code") or x.get("symbol"))
        as_of = str(x.get("entry_time") or x.get("entry_date") or "")[:10]
        rec = lookup.get((symbol, as_of))
        if rec is None:
            x["vwap_entry_status"] = "MISSING"
        else:
            x.update(rec.to_dict())
            x["vwap_entry_status"] = "OK"
        enriched.append(x)

    return enriched


def anti_chase_components(record: Mapping) -> dict:
    """
    Research-only decomposition. Returns raw features, not a trade decision.
    No threshold is considered Production-approved here.
    """
    return {
        "price_vs_vwap_pct": record.get("price_vs_vwap_pct"),
        "session_position": record.get("session_position"),
        "rvol": record.get("rvol"),
        "spread_pct": record.get("spread_pct"),
    }
