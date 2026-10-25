from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

def _parse_ts(value):
    if not value:
        return None
    try:
        dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError,ValueError):
        return None

def evaluate_source_health(
    *,
    source: str,
    observed_at: str,
    source_timestamp: Optional[str],
    freshness_sla_seconds: Optional[float],
    record_count: Optional[int]=None,
    minimum_record_count: Optional[int]=None,
    error: Optional[str]=None,
):
    observed=_parse_ts(observed_at)
    source_ts=_parse_ts(source_timestamp)
    reasons=[]
    age=None
    if error:
        reasons.append("source_error")
    if observed is None:
        reasons.append("invalid_observed_at")
    if source_ts is None:
        reasons.append("missing_source_timestamp")
    elif observed is not None:
        age=(observed-source_ts).total_seconds()
        if age < 0:
            reasons.append("future_source_timestamp")
        if freshness_sla_seconds is not None and age > float(freshness_sla_seconds):
            reasons.append("stale_source")
    if minimum_record_count is not None:
        if record_count is None or int(record_count) < int(minimum_record_count):
            reasons.append("insufficient_coverage")
    return {
        "source":source,
        "ok":not reasons,
        "status":"HEALTHY" if not reasons else "DEGRADED",
        "observed_at":observed_at,
        "source_timestamp":source_timestamp,
        "age_seconds":age,
        "freshness_sla_seconds":freshness_sla_seconds,
        "record_count":record_count,
        "minimum_record_count":minimum_record_count,
        "reasons":reasons,
        "error":error,
    }
