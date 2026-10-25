from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Iterable, Optional
import pandas as pd

DQ_SCHEMA_VERSION = "1.0.0"

@dataclass(frozen=True)
class DQReport:
    dataset: str
    coverage: float
    freshness: str
    completeness: float
    duplicates: int
    timestamp_integrity: float
    source_health: str
    status: str
    row_count: int
    schema_version: str = DQ_SCHEMA_VERSION

    def to_dict(self):
        return asdict(self)

def assess_dataframe(
    df: pd.DataFrame,
    *,
    dataset: str,
    required_columns: Optional[Iterable[str]] = None,
    timestamp_column: Optional[str] = None,
    expected_rows: Optional[int] = None,
    source_health: str = "UNKNOWN",
    max_age_seconds: Optional[int] = None,
    now: Optional[datetime] = None,
) -> dict:
    required = list(required_columns or [])
    rows = int(len(df))
    missing_required = [c for c in required if c not in df.columns]

    if expected_rows is None or expected_rows <= 0:
        coverage = 1.0 if rows > 0 else 0.0
    else:
        coverage = min(rows / expected_rows, 1.0)

    if required:
        present = [c for c in required if c in df.columns]
        completeness = float(df[present].notna().all(axis=1).mean()) if present and rows else 0.0
    else:
        completeness = 1.0 if rows else 0.0

    duplicates = int(df.duplicated().sum()) if rows else 0
    timestamp_integrity = 1.0
    freshness = "UNKNOWN"

    if timestamp_column:
        if timestamp_column not in df.columns or not rows:
            timestamp_integrity = 0.0
        else:
            ts = pd.to_datetime(df[timestamp_column], errors="coerce", utc=True)
            parsed = ts.notna()
            monotonic = bool(ts.dropna().is_monotonic_increasing)
            timestamp_integrity = float(parsed.mean()) if monotonic else 0.0
            if parsed.any():
                latest = ts[parsed].max()
                ref = now or datetime.now(timezone.utc)
                if ref.tzinfo is None:
                    ref = ref.replace(tzinfo=timezone.utc)
                age = max((ref - latest.to_pydatetime()).total_seconds(), 0)
                freshness = f"{int(age)}s"
                if max_age_seconds is not None and age > max_age_seconds:
                    freshness = f"STALE:{int(age)}s"

    src = str(source_health or "UNKNOWN").upper()
    if missing_required or rows == 0 or timestamp_integrity < 1.0:
        status = "FAIL"
    elif src in {"FAIL", "BLOCKED", "TRANSPORT_FAIL", "PARSE_SUSPECT"}:
        status = "BLOCKED"
    elif (
        coverage < 0.95
        or completeness < 0.95
        or duplicates > 0
        or freshness.startswith("STALE:")
        or src in {"UNKNOWN", "WARN"}
    ):
        status = "WARN"
    else:
        status = "PASS"

    report = DQReport(
        dataset=dataset,
        coverage=round(float(coverage), 6),
        freshness=freshness,
        completeness=round(float(completeness), 6),
        duplicates=duplicates,
        timestamp_integrity=round(float(timestamp_integrity), 6),
        source_health=src,
        status=status,
        row_count=rows,
    ).to_dict()
    report["missing_required_columns"] = missing_required
    return report
