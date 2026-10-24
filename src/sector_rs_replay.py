from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from statistics import mean
from typing import Iterable, Mapping


@dataclass(frozen=True)
class SectorRSRecord:
    symbol: str
    as_of: str
    sector: str
    stock_return: float
    sector_return: float
    market_return: float | None
    sector_rs_vs_market: float | None
    stock_rs_vs_sector: float

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "as_of": self.as_of,
            "sector": self.sector,
            "stock_return": self.stock_return,
            "sector_return": self.sector_return,
            "market_return": self.market_return,
            "sector_rs_vs_market": self.sector_rs_vs_market,
            "stock_rs_vs_sector": self.stock_rs_vs_sector,
        }


def _to_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


def _eligible_mapping(mapping_rows: Iterable[Mapping], symbol: str, as_of: date) -> str | None:
    matches = []
    for row in mapping_rows:
        if str(row.get("symbol")) != str(symbol):
            continue
        start = _to_date(row.get("effective_from") or "1900-01-01")
        end_raw = row.get("effective_to")
        end = _to_date(end_raw) if end_raw else date(9999, 12, 31)
        if start <= as_of <= end:
            matches.append((start, str(row.get("sector") or "UNKNOWN")))
    if not matches:
        return None
    matches.sort(key=lambda x: x[0], reverse=True)
    return matches[0][1]


def build_sector_rs(
    stock_returns: Iterable[Mapping],
    mapping_rows: Iterable[Mapping],
    market_returns: Mapping[str, float] | None = None,
) -> list[SectorRSRecord]:
    """
    Build point-in-time sector relative strength without using future outcomes.

    stock_returns rows require:
      symbol, as_of, lookback_return

    mapping_rows require:
      symbol, sector, effective_from, optional effective_to

    market_returns maps ISO date string -> contemporaneous market lookback return.

    Sector return is the cross-sectional mean of contemporaneous stock lookback
    returns for members whose sector mapping is effective on that as_of date.
    """
    market_returns = market_returns or {}
    prepared = []
    for row in stock_returns:
        as_of = _to_date(row["as_of"])
        sector = _eligible_mapping(mapping_rows, str(row["symbol"]), as_of)
        if sector is None:
            continue
        prepared.append(
            {
                "symbol": str(row["symbol"]),
                "as_of": as_of.isoformat(),
                "sector": sector,
                "stock_return": float(row["lookback_return"]),
            }
        )

    by_date_sector: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in prepared:
        by_date_sector[(row["as_of"], row["sector"])].append(row["stock_return"])

    sector_mean = {
        key: mean(values)
        for key, values in by_date_sector.items()
        if values
    }

    out = []
    for row in prepared:
        sec_ret = sector_mean[(row["as_of"], row["sector"])]
        mkt = market_returns.get(row["as_of"])
        out.append(
            SectorRSRecord(
                symbol=row["symbol"],
                as_of=row["as_of"],
                sector=row["sector"],
                stock_return=row["stock_return"],
                sector_return=sec_ret,
                market_return=float(mkt) if mkt is not None else None,
                sector_rs_vs_market=(sec_ret - float(mkt)) if mkt is not None else None,
                stock_rs_vs_sector=row["stock_return"] - sec_ret,
            )
        )
    return out


def attach_sector_rs_to_trades(
    trades: Iterable[Mapping],
    rs_records: Iterable[SectorRSRecord],
) -> list[dict]:
    lookup = {(r.symbol, r.as_of): r for r in rs_records}
    enriched = []
    for trade in trades:
        x = dict(trade)
        key = (str(x.get("code") or x.get("symbol")), str(x.get("entry_date"))[:10])
        rs = lookup.get(key)
        if rs is None:
            x["sector_rs_status"] = "MISSING"
        else:
            x.update(rs.to_dict())
            x["sector_rs_status"] = "OK"
        enriched.append(x)
    return enriched
