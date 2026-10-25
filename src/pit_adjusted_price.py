from __future__ import annotations

from copy import deepcopy
from typing import Iterable


ADJUSTMENT_CAPABILITY = "PIT_ASOF_EVENT_LEDGER"
ADJUSTMENT_METHOD = "SKY_BACKWARD_REFERENCE_RATIO_V1"


def adjustment_factor_for_bar(bar_date: str, as_of: str, events: Iterable[dict]) -> float:
    """Return the PIT-causal backward adjustment factor for one historical bar.

    Only corporate actions effective after the bar but on/before as_of are used.
    Events after as_of are deliberately ignored.
    """
    factor = 1.0
    for event in events or []:
        event_date = str(event.get("date") or "")
        if not event_date:
            continue
        if bar_date < event_date <= as_of:
            ratio = float(event.get("ratio"))
            if ratio <= 0:
                raise ValueError("corporate-action ratio must be positive")
            factor *= ratio
    return factor


def adjusted_bars_asof(payload: dict, as_of: str) -> list[dict]:
    """Materialize an adjusted OHLC view as it could have been known at as_of.

    The stored canonical artifact keeps raw historical OHLC. This adapter applies
    only corporate actions already effective by as_of, preventing future split /
    dividend information from changing earlier absolute-price eligibility.
    Missing bars are never synthesized or forward-filled.
    """
    payload = payload or {}
    if payload.get("adjustment_capability") != ADJUSTMENT_CAPABILITY:
        raise ValueError("payload is not PIT as-of adjustment capable")

    events = list(payload.get("corporate_action_events") or [])
    out = []
    for raw in payload.get("data") or []:
        day = str(raw.get("date") or raw.get("trading_date") or "")
        if not day or day > as_of:
            continue
        factor = adjustment_factor_for_bar(day, as_of, events)
        row = deepcopy(raw)
        row["raw_open"] = float(raw["open"])
        row["raw_high"] = float(raw["high"])
        row["raw_low"] = float(raw["low"])
        row["raw_close"] = float(raw["close"])
        row["open"] = round(float(raw["open"]) * factor, 8)
        row["high"] = round(float(raw["high"]) * factor, 8)
        row["low"] = round(float(raw["low"]) * factor, 8)
        row["close"] = round(float(raw["close"]) * factor, 8)
        row["adjusted"] = True
        row["adjusted_as_of"] = as_of
        row["adjustment_factor"] = factor
        row["adjustment_method"] = ADJUSTMENT_METHOD
        row["volume_adjusted"] = False
        out.append(row)
    return out
