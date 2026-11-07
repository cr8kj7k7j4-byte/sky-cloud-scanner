"""Sky revenue/earnings event point-in-time evidence gate.

Only vendor-verified issuer-level publication times qualify for historical
event replay. First-seen snapshots, MOPS table dates and statutory deadline
proxies are NEVER treated as verified historical publication times.

No trade signals, no orders, no automatic promotion.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

REQUIRED = ("symbol", "event_type", "period", "published_at",
            "published_at_source", "source_url", "observed_at",
            "market", "timestamp_precision", "evidence_kind")
RESEARCH_ONLY = "INSUFFICIENT_DATA"
APPROVED_KINDS = {"OFFICIAL_ISSUER_ANNOUNCEMENT", "VERIFIED_EXCHANGE_FILING"}
APPROVED_PRECISION = {"SECOND", "MINUTE"}
LATEST = {
    "TWSE_MONTHLY_REVENUE": "https://openapi.twse.com.tw/v1/opendata/t187ap05_L",
    "TPEX_MONTHLY_REVENUE": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O",
}


def parse_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO8601 string")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp must include UTC offset")
    return result


def validate_event(event: dict, signal_at: str) -> dict:
    """Explicit fail-closed PIT check; does not certify source authenticity."""
    failed: list[str] = []
    missing = [key for key in REQUIRED if not event.get(key)]
    if missing:
        failed.append("REQUIRED_EVIDENCE_MISSING")
    if event.get("evidence_kind") not in APPROVED_KINDS:
        failed.append("PUBLICATION_EVIDENCE_NOT_VERIFIED")
    if event.get("timestamp_precision") not in APPROVED_PRECISION:
        failed.append("PUBLICATION_TIMESTAMP_PRECISION_INSUFFICIENT")
    if not str(event.get("source_url", "")).startswith("https://"):
        failed.append("UNVERIFIED_URL_FORMAT")
    if not str(event.get("published_at_source", "")).strip():
        failed.append("NO_PUBLISH_TIMESTAMP_PROVENANCE")
    if event.get("event_type") not in {"MONTHLY_REVENUE", "EARNINGS_REPORT"}:
        failed.append("UNSUPPORTED_EVENT")
    if event.get("market") not in {"TWSE", "TPEX"}:
        failed.append("UNSUPPORTED_MARKET")
    try:
        pub = parse_time(event["published_at"])
        seen = parse_time(event["observed_at"])
        signal = parse_time(signal_at)
        if pub > seen:
            failed.append("FUTURE_PUBLICATION_RELATIVE_TO_CAPTURE")
        if pub > signal:
            failed.append("LOOK_AHEAD_EVENT")
        if seen > signal:
            failed.append("NOT_OBSERVED_BY_SIGNAL")
    except (KeyError, ValueError, TypeError):
        failed.append("INVALID_TIMESTAMP")
    return {
        "symbol": event.get("symbol"),
        "event_type": event.get("event_type"),
        "eligible_for_pit_replay": not failed,
        "failed": sorted(set(failed)),
        "source_authenticity_independently_verified": False,
        "production_signal": False,
    }


def audit(events: list[dict], signal_at: str) -> dict:
    assessments = [validate_event(event, signal_at) for event in events]
    count = sum(item["eligible_for_pit_replay"] for item in assessments)
    return {
        "research_state": RESEARCH_ONLY,
        "production_signal": False,
        "candidate_records": len(events),
        "structurally_eligible_for_pit": count,
        "point_in_time_eligibility_pct": round(100 * count / len(events), 4) if events else 0,
        "verified_issuer_filing_times": 0,
        "source_authenticity_review_required": True,
        "events": assessments,
        "note": "Structural timestamp checks alone never certify provenance; independently verify the actual official filing or timestamped vendor evidence.",
    }


def probe_public_tables() -> dict:
    """Checks current tables, NOT historical disclosure timestamps.

    Records HTTP/schema evidence without exporting all issuer rows.
    May run without credentials. Does not scrape archival issuer timestamps.
    """
    results = {}
    for key, url in LATEST.items():
        try:
            req = Request(url, headers={"User-Agent": "SkyResearchPITDataAudit/1.0"})
            with urlopen(req, timeout=18) as response:
                raw = response.read(12_000_000)
                content_type = response.headers.get("Content-Type", "")
                status = response.status
            try:
                rows = json.loads(raw.decode("utf-8-sig"))
                parsed = isinstance(rows, list)
                count = len(rows) if parsed else 0
                fields = list(rows[0])[:25] if parsed and count and isinstance(rows[0], dict) else []
            except (UnicodeDecodeError, ValueError, TypeError):
                parsed, count, fields = False, 0, []
            results[key] = {
                "http_status": status, "content_type": content_type,
                "json_array": parsed, "row_count": count, "sample_field_names": fields,
                "is_historical_issuer_published_at_qualified": False,
                "reason": "Latest aggregate data alone cannot establish archived issuer-level publication timestamps.",
            }
        except Exception as exc:
            results[key] = {
                "error": type(exc).__name__ + ": " + str(exc)[:160],
                "is_historical_issuer_published_at_qualified": False,
            }
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-latest", action="store_true")
    parser.add_argument("--events", help="JSON list of evidence records (optional)")
    parser.add_argument("--signal-at", default="2026-11-08T00:00:00+08:00")
    parser.add_argument("--output", default="research_output/disclosure_pit_audit.json")
    args = parser.parse_args()
    events = []
    if args.events:
        with open(args.events, encoding="utf-8") as f:
            events = json.load(f)
        if not isinstance(events, list):
            raise ValueError("event input must be a JSON list")
    result = audit(events, args.signal_at)
    result["latest_public_table_probe"] = probe_public_tables() if args.probe_latest else None
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": result["research_state"],
        "candidate_records": result["candidate_records"],
        "structurally_eligible_for_pit": result["structurally_eligible_for_pit"],
        "latest_public_table_probe": result["latest_public_table_probe"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
