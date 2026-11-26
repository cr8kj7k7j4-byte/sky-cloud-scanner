"""SKY維持率: join already obtained source datasets without networking.

One shared full-universe row ledger -> existing #749 four-factor filter; raw
Fugle A2 quote evidence handled by #750. No providers are called here.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from src.sky_margin_a2_quote_bridge import margin_row_with_a2_quote
from src.sky_margin_research_filter import filter_margin_observations


def _feed(source: Mapping[str, Mapping[str, Any]], allowed: set[str], label: str):
    if not isinstance(source, Mapping):
        raise ValueError("INVALID_" + label + "_FEED")
    if set(source) - allowed:
        raise ValueError("EXTRA_" + label + "_SYMBOLS")
    if any(not isinstance(row, Mapping) for row in source.values()):
        raise ValueError("INVALID_" + label + "_ROW")


def join_margin_sources(
    official_universe: Sequence[Mapping[str, Any]], *,
    universe_total: int, official_universe_source: str,
    ratio_by_symbol: Mapping[str, Mapping[str, Any]],
    capital_by_symbol: Mapping[str, Mapping[str, Any]],
    volume_by_symbol: Mapping[str, Mapping[str, Any]],
    fugle_quotes_by_symbol: Mapping[str, Mapping[str, Any]],
    observed_at: datetime, previous_session_date: str,
) -> dict[str, Any]:
    """Combine upstream provided records, never download or authorize trades.

    Each source record carries the #749 standard fields and source/date.
    The universe and its official source are caller assertions (not remote proofs).
    A2 quotes must be independently authenticated by the upstream collector.
    """
    if not isinstance(official_universe, (tuple, list)):
        raise ValueError("INVALID_OFFICIAL_UNIVERSE")
    if not isinstance(observed_at, datetime) or observed_at.utcoffset() is None:
        raise ValueError("INVALID_OBSERVATION_TIME")
    symbols = []
    for record in official_universe:
        if not isinstance(record, Mapping):
            raise ValueError("INVALID_UNIVERSE_RECORD")
        symbol = str(record.get("symbol") or "").strip()
        if not symbol.isdigit() or not 4 <= len(symbol) <= 6 or record.get("exchange") not in ("TWSE", "TPEx"):
            raise ValueError("INVALID_UNIVERSE_IDENTITY")
        symbols.append(symbol)
    if len(symbols) != len(set(symbols)):
        raise ValueError("DUPLICATE_OFFICIAL_SYMBOL")
    allowed = set(symbols)
    for source, label in (
        (ratio_by_symbol, "RATIO"), (capital_by_symbol, "CAPITAL"),
        (volume_by_symbol, "VOLUME"), (fugle_quotes_by_symbol, "A2"),
    ):
        _feed(source, allowed, label)

    rows = []
    for item in official_universe:
        symbol = str(item["symbol"])
        row = {"symbol": symbol, "exchange": item["exchange"]}
        ratio = ratio_by_symbol.get(symbol, {})
        capital = capital_by_symbol.get(symbol, {})
        volume = volume_by_symbol.get(symbol, {})
        for data, keys in (
            (ratio, ("margin_ratio_pct", "ratio_source", "ratio_date", "ratio_method")),
            (capital, ("paid_in_capital_twd", "capital_source", "capital_date")),
            (volume, ("previous_volume_lots", "volume_source", "volume_date")),
        ):
            for key in keys:
                if key in data:
                    row[key] = data[key]
        raw_quote = fugle_quotes_by_symbol.get(symbol)
        if raw_quote is not None:
            row = margin_row_with_a2_quote(row, raw_quote, observed_at=observed_at)
        rows.append(row)

    result = filter_margin_observations(
        rows, observation_date=observed_at.date().isoformat(),
        previous_session_date=previous_session_date,
        universe_total=universe_total,
        universe_source=official_universe_source,
    )
    result.update({
        "source_join": "CALLER_SUPPLIED_MULTI_SOURCE_RESEARCH_ONLY",
        "official_universe_independently_verified": False,
        "provider_entitlement_verified": False,
        "http_source_provenance_verified": False,
        "a2_quote_records_supplied": len(fugle_quotes_by_symbol),
        "missing_ratio_records": sum(symbol not in ratio_by_symbol for symbol in symbols),
        "missing_capital_records": sum(symbol not in capital_by_symbol for symbol in symbols),
        "missing_volume_records": sum(symbol not in volume_by_symbol for symbol in symbols),
        "missing_a2_quote_records": sum(symbol not in fugle_quotes_by_symbol for symbol in symbols),
        "buy_eligible": False, "trade_status": "NO_TRADE",
    })
    return result
