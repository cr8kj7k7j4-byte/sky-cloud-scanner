"""Research-only evidence intake for Issue #190; never a PIT approval."""
import argparse
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo("Asia/Taipei")
FIELDS = ("provider", "symbol", "license_evidence", "availability_evidence",
          "calendar_evidence", "coverage_evidence", "adjustment_policy")
REQUIRED = {"SOX", "NASDAQ100", "VIX", "TW_INDEX_0900_0930"}


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timezone required")
    return parsed


def audit(data):
    errors = []
    if not isinstance(data, dict):
        return {"status": "HOLD", "errors": ["manifest must be an object"], "gate0": "NOT_PROVEN"}
    sources = data.get("sources")
    if not isinstance(sources, list):
        sources = []
        errors.append("sources must be a list")
    indexed = {}
    for source in sources:
        if not isinstance(source, dict):
            errors.append("source must be an object")
            continue
        name = source.get("name")
        if not isinstance(name, str) or name not in REQUIRED:
            errors.append("unknown source name")
            continue
        if name in indexed:
            errors.append(f"{name}: duplicate source")
        indexed[name] = source
        for field in FIELDS:
            if not isinstance(source.get(field), str) or not source[field].strip():
                errors.append(f"{name}: missing {field}")
    for name in sorted(REQUIRED - indexed.keys()):
        errors.append(f"{name}: missing source")
    rows = data.get("observations")
    if not isinstance(rows, list) or not rows:
        errors.append("no observations to audit")
        rows = []
    seen = set()
    for i, row in enumerate(rows):
        try:
            if not isinstance(row, dict):
                raise ValueError("observation must be an object")
            name = row.get("name")
            if name not in REQUIRED - {"TW_INDEX_0900_0930"}:
                raise ValueError("unknown input name")
            taiwan_day = dt.date.fromisoformat(row["taiwan_session"])
            us_day = dt.date.fromisoformat(row["us_session"])
            key = (taiwan_day, name)
            if key in seen:
                errors.append(f"row {i}: duplicate session and input")
            seen.add(key)
            published = _timestamp(row.get("published_at"))
            available = _timestamp(row.get("available_at"))
            cutoff = dt.datetime.combine(taiwan_day, dt.time(8, 30), TAIPEI)
            if us_day >= taiwan_day:
                errors.append(f"row {i}: US session is not prior to Taiwan session")
            if published > available:
                errors.append(f"row {i}: availability precedes publication")
            if available > cutoff:
                errors.append(f"row {i}: available after 08:30 Taiwan")
            if not isinstance(row.get("record_evidence"), str) or not row["record_evidence"].strip():
                errors.append(f"row {i}: missing record_evidence")
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f"row {i}: invalid observation ({exc})")
    for day in {day for day, _ in seen}:
        for name in (REQUIRED - {"TW_INDEX_0900_0930"}):
            if (day, name) not in seen:
                errors.append(f"{day}: missing {name}")
    return {"status": "HOLD" if errors else "REVIEW_REQUIRED", "gate0": "NOT_PROVEN",
            "errors": sorted(errors), "observations_checked": len(rows),
            "limitations": ["Evidence strings are unverified claims, not source or license validation.",
                            "US/TW holiday and early-close calendar mapping requires independent audit.",
                            "Taiwan index outcome, price values, revisions, coverage and data latency require audit.",
                            "No strategy, pre-registration, performance or promotion decision is made."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        result = audit(json.loads(args.manifest.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        result = {"status": "HOLD", "gate0": "NOT_PROVEN", "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "HOLD" else 0


if __name__ == "__main__":
    raise SystemExit(main())
