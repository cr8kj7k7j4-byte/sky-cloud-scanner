from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional


TIME_BUCKETS = (
    ("09:00-09:05", time(9, 0), time(9, 5)),
    ("09:05-09:15", time(9, 5), time(9, 15)),
    ("09:15-09:30", time(9, 15), time(9, 30)),
    ("09:30-09:50", time(9, 30), time(9, 50)),
    ("09:50-10:15", time(9, 50), time(10, 15)),
)


def classify_time_bucket(ts: datetime) -> str:
    t = ts.timetz().replace(tzinfo=None)
    for label, start, end in TIME_BUCKETS:
        if start <= t < end:
            return label
    return "10:15+" if t >= time(10, 15) else "PRE_OPEN"


def classify_price_bucket(price: float) -> str:
    if price <= 0:
        raise ValueError("price must be positive")
    if price < 20:
        return "<20"
    if price < 50:
        return "20-50"
    if price <= 100:
        return "50-100"
    return ">100_RESEARCH_ONLY"


def spread_bps(bid: Optional[float], ask: Optional[float]) -> Optional[float]:
    if bid is None or ask is None:
        return None
    bid = float(bid)
    ask = float(ask)
    if bid <= 0 or ask <= 0 or ask < bid:
        return None
    mid = (bid + ask) / 2.0
    return ((ask - bid) / mid) * 10000.0 if mid else None


def long_entry_slippage_bps(reference_price: Optional[float], fill_price: Optional[float]) -> Optional[float]:
    if reference_price in (None, 0) or fill_price is None:
        return None
    return (float(fill_price) / float(reference_price) - 1.0) * 10000.0


def long_exit_slippage_bps(reference_price: Optional[float], fill_price: Optional[float]) -> Optional[float]:
    if reference_price in (None, 0) or fill_price is None:
        return None
    return (1.0 - float(fill_price) / float(reference_price)) * 10000.0


def slippage_in_r(reference_price: Optional[float], fill_price: Optional[float], risk_per_share: Optional[float]) -> Optional[float]:
    if reference_price is None or fill_price is None or risk_per_share in (None, 0):
        return None
    return (float(fill_price) - float(reference_price)) / float(risk_per_share)


def signed_forward_return_long(fill_price: Optional[float], future_price: Optional[float]) -> Optional[float]:
    if fill_price in (None, 0) or future_price is None:
        return None
    return float(future_price) / float(fill_price) - 1.0


def adverse_selection_long(fill_price: Optional[float], future_price: Optional[float]) -> Optional[bool]:
    ret = signed_forward_return_long(fill_price, future_price)
    return None if ret is None else ret < 0


@dataclass(frozen=True)
class W6L1ExecutionSample:
    symbol: str
    observation_timestamp: str
    execution_type: str
    reference_price: Optional[float]
    bid: Optional[float]
    ask: Optional[float]
    fill_status: str
    fill_price: Optional[float] = None
    risk_per_share: Optional[float] = None
    future_price_1m: Optional[float] = None
    future_price_3m: Optional[float] = None
    future_price_5m: Optional[float] = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        try:
            ts = datetime.fromisoformat(self.observation_timestamp.replace("Z", "+00:00"))
        except Exception:
            errors.append("INVALID_OBSERVATION_TIMESTAMP")
            ts = None
        if ts is not None and ts.tzinfo is None:
            errors.append("TIMESTAMP_NOT_TIMEZONE_AWARE")
        if self.fill_status not in {"FILLED", "PARTIAL", "MISSED", "CANCELLED", "REJECTED", "UNKNOWN"}:
            errors.append("INVALID_FILL_STATUS")
        if self.fill_status in {"FILLED", "PARTIAL"} and self.fill_price is None:
            errors.append("FILL_PRICE_REQUIRED")
        if self.fill_status in {"MISSED", "CANCELLED", "REJECTED"} and self.fill_price is not None:
            errors.append("NON_FILL_MUST_NOT_HAVE_FILL_PRICE")
        if self.bid is not None and self.ask is not None and float(self.ask) < float(self.bid):
            errors.append("CROSSED_OR_INVALID_QUOTE")
        return errors

    def metrics(self) -> dict:
        errors = self.validate()
        try:
            ts = datetime.fromisoformat(self.observation_timestamp.replace("Z", "+00:00"))
        except Exception:
            ts = None
        px = self.reference_price or self.fill_price
        filled = self.fill_status in {"FILLED", "PARTIAL"}
        return {
            "status": "OK" if not errors else "INVALID",
            "errors": errors,
            "time_bucket": classify_time_bucket(ts) if ts else None,
            "price_bucket": classify_price_bucket(float(px)) if px not in (None, 0) else None,
            "spread_bps": spread_bps(self.bid, self.ask),
            "entry_slippage_bps": long_entry_slippage_bps(self.reference_price, self.fill_price) if filled else None,
            "slippage_r": slippage_in_r(self.reference_price, self.fill_price, self.risk_per_share) if filled else None,
            "adverse_selection_1m": adverse_selection_long(self.fill_price, self.future_price_1m) if filled else None,
            "adverse_selection_3m": adverse_selection_long(self.fill_price, self.future_price_3m) if filled else None,
            "adverse_selection_5m": adverse_selection_long(self.fill_price, self.future_price_5m) if filled else None,
        }


def aggregate_fill_rates(rows: list[W6L1ExecutionSample]) -> dict:
    n = len(rows)
    if n == 0:
        return {"sample": 0, "fill_rate": None, "missed_trade_rate": None, "status": "INSUFFICIENT_DATA"}
    filled = sum(r.fill_status in {"FILLED", "PARTIAL"} for r in rows)
    missed = sum(r.fill_status == "MISSED" for r in rows)
    return {
        "sample": n,
        "fill_rate": filled / n,
        "missed_trade_rate": missed / n,
        "status": "EARLY_SAMPLE" if n < 20 else "BASELINE_READY",
    }
