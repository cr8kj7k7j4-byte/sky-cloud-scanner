"""Forward-only official disclosure snapshot evidence collector.

Records immutable per-execution raw response bytes, sha256 and first *observation*
time. Does not backdate availability or claim original issuer publication time.
Mode is READ_ONLY, NO TRADE SIGNALS, no direct brokerage calls.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import time
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SOURCES = {
    "twse_revenue_latest": "https://openapi.twse.com.tw/v1/opendata/t187ap05_L",
    "tpex_revenue_latest": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O",
    "twse_material_latest": "https://openapi.twse.com.tw/v1/opendata/t187ap04_L",
    "tpex_material_latest": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O",
}
MAX_BYTES = 15_000_000


def capture_one(label: str, url: str, directory: Path) -> dict:
    """Write exact source bytes before parsing. Error is fail-closed."""
    observed_start = datetime.now(timezone.utc).isoformat()
    row = {"source": label, "url": url, "request_started_at_utc": observed_start,
           "qualified_issuer_published_at": False, "usable_historical_pit": False}
    try:
        payload = None
        # A rate-limited exchange endpoint may recover; do not loop indefinitely.
        for attempt in range(3):
            row["attempts"] = attempt + 1
            try:
                with urlopen(Request(url, headers={"User-Agent": "SkyDisclosureEvidenceCollector/1.0",
                                                  "Accept": "application/json"}), timeout=30) as response:
                    payload = response.read(MAX_BYTES + 1)
                    row["http_status"] = response.status
                    row["content_type"] = response.headers.get("Content-Type", "")
                row["observed_at_utc"] = datetime.now(timezone.utc).isoformat()
                break
            except HTTPError as exc:
                row["http_status"] = exc.code
                row["last_http_error"] = exc.code
                if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                    raise
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise
            time.sleep(1.5 * (attempt + 1))
        if payload is None:
            raise ValueError("no HTTP response payload")
        if len(payload) > MAX_BYTES:
            raise ValueError("response size limit exceeded")
        if row["http_status"] != 200:
            raise ValueError("non-200 response")
        parsed = json.loads(payload.decode("utf-8-sig"))
        if not isinstance(parsed, list) or not parsed:
            raise ValueError("invalid or empty JSON array")
        if not isinstance(parsed[0], dict):
            raise ValueError("issuer records are not objects")
        raw_sha = hashlib.sha256(payload).hexdigest()
        directory.mkdir(parents=True, exist_ok=True)
        raw_path = directory / (label + ".raw.json")
        raw_path.write_bytes(payload)
        row.update({
            "fetch_status": "CAPTURED",
            "sha256": raw_sha,
            "bytes": len(payload),
            "row_count": len(parsed),
            "field_names": list(parsed[0].keys()),
            "raw_file": raw_path.name,
            "classification": "FIRST_SEEN_SNAPSHOT_ONLY_NOT_ORIGINAL_FILING_TIME",
        })
    except Exception as exc:
        row.update({"fetch_status": "ERROR",
                    "error_type": type(exc).__name__})
    return row


def run(directory: Path, fetcher=capture_one) -> dict:
    observations = {label: fetcher(label, url, directory) for label, url in SOURCES.items()}
    success = all(item.get("fetch_status") == "CAPTURED" for item in observations.values())
    report = {
        "model": "DISCLOSURE_FORWARD_EVIDENCE_CAPTURE_V1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "SNAPSHOT_CAPTURED_RESEARCH_ONLY" if success else "INCOMPLETE_DATA",
        "production_signal": False,
        "historical_issuer_publication_timestamp_qualified": False,
        "historical_pit_event_count": 0,
        "source_results": observations,
        "long_term_storage": "NOT_VERIFIED",
        "retention_risk": "GitHub Actions artifacts expire; this run is not a durable archive.",
        "note": "First observed is not published_at. Current aggregate tables never establish issuer historical event timestamps.",
    }
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="research_output/disclosure_forward_snapshot")
    a=ap.parse_args()
    result=run(Path(a.out_dir))
    print(json.dumps({
        "status": result["status"],
        "source_results": {
            k: {"fetch_status": v.get("fetch_status"), "rows": v.get("row_count"),
                "sha256": v.get("sha256"), "observed_at_utc": v.get("observed_at_utc"),
                "error_type": v.get("error_type"), "http": v.get("http_status"), "attempts": v.get("attempts")}
            for k, v in result["source_results"].items()},
        "production_signal": False,
        "historical_pit_event_count": 0,
    }, ensure_ascii=False))


if __name__=="__main__":
    main()
