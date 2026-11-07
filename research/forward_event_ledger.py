"""Forward-only provisional event ledger from audited official snapshots.

No inference of issuer's original published_at. Each first observation is
recorded; a changed payload becomes a revision (not a new independent trade).
Research data only. Input must pass the four-source SHA-256 provenance gate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from research.disclosure_gcs_readback import validate_capture, REQUIRED

LABELS = {
    "twse_revenue_latest": ("TWSE", "MONTHLY_REVENUE"),
    "tpex_revenue_latest": ("TPEX", "MONTHLY_REVENUE"),
    "twse_material_latest": ("TWSE", "MATERIAL_DISCLOSURE"),
    "tpex_material_latest": ("TPEX", "MATERIAL_DISCLOSURE"),
}


def canonical_bytes(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def hash_dict(obj):
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def iso_aware(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("invalid observed-at time zone")
    return result


def pick_field(item, names):
    for name in names:
        x = item.get(name)
        if x is not None and str(x).strip():
            return str(x).strip()
    return ""


def provisional_event_key(source, item):
    """Not an official filing ID; never certify official uniqueness."""
    if source not in LABELS or not isinstance(item, dict):
        raise ValueError("unrecognized source or row")
    symbol = pick_field(item, ["公司代號", "SecuritiesCompanyCode", "stock_id", "symbol"])
    if not symbol:
        raise ValueError("issuer identifier missing")
    _, category = LABELS[source]
    if category == "MONTHLY_REVENUE":
        period = pick_field(item, ["資料年月", "YearMonth", "period"])
        if not period:
            raise ValueError("revenue period missing")
        identity = {"source": source, "symbol": symbol, "category": category,
                    "period": period}
    else:
        title = pick_field(item, ["主旨", "主旨 ", "Subject"])
        release_date = pick_field(item, ["發言日期", "Date", "ReleaseDate"])
        release_time = pick_field(item, ["發言時間", "ReleaseTime"])
        if not title or not release_date:
            raise ValueError("disclosure title/date missing")
        identity = {"source": source, "symbol": symbol, "category": category,
                    "title": title, "reported_date": release_date,
                    "reported_time": release_time}
    return hash_dict(identity), identity


def build_ledger(snapshot_directory: Path, previous: dict | None = None):
    validate_capture(snapshot_directory)  # cryptographically verify raw bytes
    manifest = json.loads((snapshot_directory / "manifest.json").read_text(encoding="utf-8"))
    if previous:
        if previous.get("production_signal") is not False:
            raise ValueError("untrusted previous ledger")
        events = dict(previous.get("events", {}))
    else:
        events = {}
    counter = {"added": 0, "unchanged": 0, "revision": 0,
               "skipped_invalid": 0, "duplicate_rows_within_snapshot": 0}
    collisions = set()
    for source in REQUIRED:
        spec = manifest["source_results"][source]
        observed = spec["observed_at_utc"]
        new_time = iso_aware(observed)
        items = json.loads((snapshot_directory / spec["raw_file"]).read_text(encoding="utf-8-sig"))
        for row in items:
            try:
                key, identity = provisional_event_key(source, row)
            except (TypeError, ValueError):
                counter["skipped_invalid"] += 1
                continue
            fingerprint = hash_dict(row)
            seen_key = (source, key, fingerprint)
            if seen_key in collisions:
                counter["duplicate_rows_within_snapshot"] += 1
                continue
            collisions.add(seen_key)
            existing = events.get(key)
            if existing:
                if iso_aware(existing["first_observed_at_utc"]) > new_time:
                    raise ValueError("snapshot older than prior first observation")
                if fingerprint == existing["revisions"][-1]["payload_sha256"]:
                    counter["unchanged"] += 1
                    continue
                revision = len(existing["revisions"]) + 1
                existing["revisions"].append({
                    "revision": revision, "first_observed_at_utc": observed,
                    "payload_sha256": fingerprint, "raw_source_sha256": spec["sha256"],
                    "raw_payload": row, "verification": "OBSERVED_CHANGE_NOT_OFFICIAL_AMENDMENT",
                })
                counter["revision"] += 1
            else:
                events[key] = {
                    "provisional_key_sha256": key,
                    "provisional_identity": identity,
                    "first_observed_at_utc": observed,
                    "issuer_original_published_at": None,
                    "issuer_publication_source_verified": False,
                    "independent_trading_event": False,
                    "revisions": [{
                        "revision": 1, "first_observed_at_utc": observed,
                        "payload_sha256": fingerprint, "raw_source_sha256": spec["sha256"],
                        "raw_payload": row,
                        "verification": "OBSERVED_SNAPSHOT_ONLY",
                    }],
                }
                counter["added"] += 1
    report = {
        "model": "DISCLOSURE_PROVISIONAL_FORWARD_EVENT_LEDGER_V1",
        "status": "OBSERVED_ONLY_NOT_PIT_ELIGIBLE",
        "production_signal": False, "eligible_trade_events": 0,
        "historical_pit_certified": False,
        "source_first_observation_not_publication": True,
        "counts": counter, "unique_provisional_events": len(events),
        "events": events,
    }
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default="research_output/disclosure_forward_snapshot")
    ap.add_argument("--previous", default="")
    ap.add_argument("--out", default="research_output/disclosure_provisional_events.json")
    args = ap.parse_args()
    previous = json.loads(Path(args.previous).read_text(encoding="utf-8")) if args.previous else None
    ledger = build_ledger(Path(args.folder), previous)
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": ledger["status"], "unique_provisional_events": ledger["unique_provisional_events"],
        "counts": ledger["counts"], "eligible_trade_events": ledger["eligible_trade_events"],
        "production_signal": ledger["production_signal"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
