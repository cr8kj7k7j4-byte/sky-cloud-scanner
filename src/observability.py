from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass(frozen=True)
class ServiceMetric:
    service: str
    available: bool
    latency_ms: float | None = None
    freshness_seconds: float | None = None
    error_rate: float | None = None
    success_rate: float | None = None
    checked_at: str | None = None
    detail: str = ""

    def to_dict(self):
        item = asdict(self)
        item["checked_at"] = item["checked_at"] or datetime.now(timezone.utc).isoformat()
        return item


def health_snapshot(metrics):
    rows=[]
    for m in metrics or []:
        rows.append(m if isinstance(m,ServiceMetric) else ServiceMetric(**m))

    unavailable=[m.service for m in rows if not m.available]
    return {
        "services":[m.to_dict() for m in rows],
        "service_count":len(rows),
        "unavailable_services":unavailable,
        "all_available":not unavailable,
        "generated_at":datetime.now(timezone.utc).isoformat(),
    }
