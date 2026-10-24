from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import csv
from statistics import median
from typing import Iterable, Optional


DEFAULT_LEDGER_PATH = Path("output/private/execution_calibration.csv")


@dataclass(frozen=True)
class ExecutionCalibrationSample:
    trade_date: str
    transaction_mode: str
    shares: int
    buy_price: float
    sell_price: float
    buy_commission_twd: float
    sell_commission_twd: float
    sell_tax_twd: float
    financing_interest_twd: float = 0.0
    expected_entry_price: Optional[float] = None
    expected_exit_price: Optional[float] = None
    observed_spread_bps: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def buy_notional(self) -> float:
        return self.buy_price * self.shares

    @property
    def sell_notional(self) -> float:
        return self.sell_price * self.shares

    @property
    def buy_commission_rate(self) -> float:
        return self.buy_commission_twd / self.buy_notional if self.buy_notional else 0.0

    @property
    def sell_commission_rate(self) -> float:
        return self.sell_commission_twd / self.sell_notional if self.sell_notional else 0.0

    @property
    def sell_tax_rate(self) -> float:
        return self.sell_tax_twd / self.sell_notional if self.sell_notional else 0.0

    @property
    def entry_slippage_bps(self) -> Optional[float]:
        if self.expected_entry_price in (None, 0):
            return None
        return (self.buy_price / float(self.expected_entry_price) - 1.0) * 10000.0

    @property
    def exit_slippage_bps(self) -> Optional[float]:
        if self.expected_exit_price in (None, 0):
            return None
        return (1.0 - self.sell_price / float(self.expected_exit_price)) * 10000.0


FIELDS = [
    "trade_date","transaction_mode","shares","buy_price","sell_price",
    "buy_commission_twd","sell_commission_twd","sell_tax_twd",
    "financing_interest_twd","expected_entry_price","expected_exit_price",
    "observed_spread_bps",
]


def append_sample(sample: ExecutionCalibrationSample, path: Path | str = DEFAULT_LEDGER_PATH) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    exists = p.exists()
    with p.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(sample.to_dict())
    return p


def load_samples(path: Path | str = DEFAULT_LEDGER_PATH) -> list[ExecutionCalibrationSample]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    with p.open("r", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out.append(ExecutionCalibrationSample(
                trade_date=row["trade_date"],
                transaction_mode=row["transaction_mode"],
                shares=int(row["shares"]),
                buy_price=float(row["buy_price"]),
                sell_price=float(row["sell_price"]),
                buy_commission_twd=float(row["buy_commission_twd"]),
                sell_commission_twd=float(row["sell_commission_twd"]),
                sell_tax_twd=float(row["sell_tax_twd"]),
                financing_interest_twd=float(row.get("financing_interest_twd") or 0),
                expected_entry_price=float(row["expected_entry_price"]) if row.get("expected_entry_price") else None,
                expected_exit_price=float(row["expected_exit_price"]) if row.get("expected_exit_price") else None,
                observed_spread_bps=float(row["observed_spread_bps"]) if row.get("observed_spread_bps") else None,
            ))
    return out


def summarize_calibration(samples: Iterable[ExecutionCalibrationSample]) -> dict:
    rows = list(samples)
    if not rows:
        return {"sample_count": 0, "status": "INSUFFICIENT_DATA"}

    buy_rates = [x.buy_commission_rate for x in rows]
    sell_rates = [x.sell_commission_rate for x in rows]
    tax_rates = [x.sell_tax_rate for x in rows]

    entry_slip = [x.entry_slippage_bps for x in rows if x.entry_slippage_bps is not None]
    exit_slip = [x.exit_slippage_bps for x in rows if x.exit_slippage_bps is not None]
    spreads = [x.observed_spread_bps for x in rows if x.observed_spread_bps is not None]

    return {
        "sample_count": len(rows),
        "status": "CALIBRATION_READY" if len(rows) >= 20 else "EARLY_SAMPLE",
        "commission_buy_median": median(buy_rates),
        "commission_sell_median": median(sell_rates),
        "sell_tax_median": median(tax_rates),
        "entry_slippage_bps_median": median(entry_slip) if entry_slip else None,
        "exit_slippage_bps_median": median(exit_slip) if exit_slip else None,
        "spread_bps_median": median(spreads) if spreads else None,
        "slippage_sample_count": min(len(entry_slip), len(exit_slip)),
        "spread_sample_count": len(spreads),
    }
