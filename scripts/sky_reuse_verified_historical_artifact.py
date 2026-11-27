"""W0 #363: reuse *verified* Fugle historical Artifact in ordinary Sky reports.

No Fugle calls. Independently validate source Run/attempt/SHA/Artifact ID,
downloaded file digests, dated provider identity and research-only flags.
The same evidence contract can be consumed by daytrade, swing or single-stock.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TPE = timezone(timedelta(hours=8))
HISTORY_PASS = "PASS_COMPLETED_HISTORICAL_5M_RESEARCH_ONLY"
NO_BARS = "OBSERVATION_ONLY_NO_5M_BARS"
PASS = "PASS_VERIFIED_HISTORICAL_ARTIFACT_REUSE_RESEARCH_ONLY"


def verify_history(source_dir, receipt_dir, *, symbol, run_id, head_sha,
                   artifact_id, observed_at=None):
    now = observed_at or datetime.now(TPE)
    if not (isinstance(symbol, str) and re.fullmatch(r"[0-9]{4,6}", symbol)
            and str(run_id).isdecimal()
            and isinstance(head_sha, str) and re.fullmatch(r"[0-9a-f]{40}", head_sha)
            and type(artifact_id) is int and artifact_id > 0):
        raise ValueError("INVALID_VERIFIED_HISTORY_EXPECTATION")
    root = Path(source_dir).resolve(strict=True)
    receipts = Path(receipt_dir).resolve(strict=True)
    source_file = root / f"{symbol}-5m-source.json"
    markdown_file = root / f"{symbol}-5m-source.md"
    receipt_file = receipts / "receipt.json"
    for f, parent in ((source_file, root), (markdown_file, root),
                      (receipt_file, receipts)):
        if not f.is_file() or f.is_symlink() or f.resolve().parent != parent:
            raise ValueError("MISSING_OR_UNSAFE_HISTORY_ARTIFACT")
        if f.stat().st_size > 4_000_000:
            raise ValueError("HISTORY_ARTIFACT_TOO_LARGE")
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    if (not isinstance(receipt, dict)
            or receipt.get("schema") != "SKY_SINGLE_STOCK_SAME_RUN_READBACK_V1"
            or receipt.get("status") != "PASS_ARTIFACT_INTEGRITY_RESEARCH_ONLY"
            or str(receipt.get("run_id")) != str(run_id)
            or str(receipt.get("attempt")) != "1"
            or receipt.get("head_sha") != head_sha
            or receipt.get("artifact_id") != artifact_id
            or receipt.get("symbol") != symbol
            or receipt.get("execution_authorized") is not False
            or receipt.get("automatic_order") is not False
            or receipt.get("production_eligible") is not False
            or receipt.get("file_count") != 2):
        raise ValueError("UNVERIFIED_HISTORICAL_READBACK_IDENTITY")
    expected = receipt.get("file_sha256")
    if not isinstance(expected, dict) or set(expected) != {
            source_file.name, markdown_file.name}:
        raise ValueError("INVALID_HISTORICAL_FILE_INVENTORY")
    for f in (source_file, markdown_file):
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        if expected.get(f.name) != digest:
            raise ValueError("HISTORICAL_ARTIFACT_DIGEST_MISMATCH")
    payload = json.loads(source_file.read_text(encoding="utf-8"))
    history = payload.get("historical_5m_research") if isinstance(payload, dict) else None
    if not isinstance(history, dict):
        raise ValueError("HISTORICAL_RESEARCH_EVIDENCE_MISSING")
    day_string = payload.get("source_date")
    try:
        session_day = date.fromisoformat(day_string)
    except (TypeError, ValueError) as exc:
        raise ValueError("INVALID_HISTORICAL_SESSION_DATE") from exc
    if (session_day >= now.astimezone(TPE).date()
            or payload.get("symbol") != symbol
            or payload.get("http_status") != 200
            or payload.get("status") not in (HISTORY_PASS, NO_BARS)
            or history.get("status") != payload.get("status")
            or history.get("symbol") != symbol
            or history.get("source_date") != day_string
            or history.get("execution_authorized") is not False
            or history.get("automatic_order") is not False
            or history.get("production_eligible") is not False
            or history.get("independent_vwap_certified") is not False
            or history.get("executed_trade_time_certified") is not False
            or not isinstance(payload.get("provider_metadata"), dict)
            or payload["provider_metadata"].get("symbol") != symbol
            or payload["provider_metadata"].get("exchange") not in ("TWSE", "TPEx")
            or payload["provider_metadata"].get("timeframe") != "5"):
        raise ValueError("HISTORICAL_SOURCE_IDENTITY_OR_SAFETY_MISMATCH")
    count = payload.get("row_count")
    bars = history.get("bars")
    if (type(count) is not int or count < 0 or type(bars) is not list
            or len(bars) != count
            or history.get("completed_bar_count") != count
            or (count == 0 and payload.get("status") != NO_BARS)
            or (count > 0 and payload.get("status") != HISTORY_PASS)):
        raise ValueError("HISTORICAL_COUNT_INCONSISTENT")
    # Readback proves the origin and integrity of this historical observation,
    # NOT that it is the current/latest trading day or an executable price.
    return {
        "status": PASS,
        "symbol": symbol,
        "source_date": day_string,
        "observed_at_tpe": now.astimezone(TPE).isoformat(),
        "source": "Fugle Historical Candles / verified GitHub Artifact",
        "source_run_id": str(run_id),
        "source_head_sha": head_sha,
        "source_artifact_id": artifact_id,
        "source_attempt": 1,
        "source_json_sha256": expected[source_file.name],
        "http_status_original_observation": 200,
        "request_count_for_reuse": 0,
        "kbar_evidence_level": history.get("kbar_evidence_level"),
        "completed_bar_count": count,
        "historical_5m_research": history,
        "execution_authorized": False,
        "independent_vwap_certified": False,
        "production_eligible": False,
        "automatic_order": False,
    }


def attach_to_report(*, report_dir, evidence, symbol):
    """Enrich a normal same-run single-stock report without new market calls."""
    root = Path(report_dir)
    src = root / f"{symbol}-5m-source.json"
    if not src.is_file():
        raise ValueError("CURRENT_REPORT_MISSING")
    audit = json.loads(src.read_text(encoding="utf-8"))
    if audit.get("symbol") != symbol:
        raise ValueError("CURRENT_SYMBOL_MISMATCH")
    if evidence.get("status") != PASS or evidence.get("symbol") != symbol:
        raise ValueError("UNVERIFIED_HISTORICAL_REUSE")
    history = dict(evidence["historical_5m_research"])
    history["source_run_id"] = evidence["source_run_id"]
    history["source_artifact_id"] = evidence["source_artifact_id"]
    history["source_head_sha"] = evidence["source_head_sha"]
    history["source_json_sha256"] = evidence["source_json_sha256"]
    history["reused_no_new_fugle_http"] = True
    audit["historical_5m_research"] = history
    audit["historical_artifact_reuse"] = {
        k: v for k, v in evidence.items()
        if k not in ("historical_5m_research",)
    }
    if (audit.get("execution_authorized") is not False
            or audit.get("automatic_order") is not False):
        raise ValueError("CURRENT_REPORT_NOT_RESEARCH_ONLY")
    src.write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    from src.sky_single_stock_source_audit import render_mobile_source_audit, render_unified_stock_research
    (root / f"{symbol}-5m-source.md").write_text(render_mobile_source_audit(audit), encoding="utf-8")
    unified_file = root / f"{symbol}.json"
    if unified_file.is_file():
        unified = json.loads(unified_file.read_text(encoding="utf-8"))
        if unified.get("symbol") != symbol or unified.get("execution_authorized") is not False:
            raise ValueError("CURRENT_UNIFIED_REPORT_INVALID")
        unified["source_audit"] = audit
        unified_file.write_text(json.dumps(unified, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (root / f"{symbol}.md").write_text(
            render_unified_stock_research(audit, unified.get("observation") or {}),
            encoding="utf-8")
    return {"status": PASS, "symbol": symbol, "source_date": history["source_date"],
            "request_count_for_reuse": 0}


def main():
    p = argparse.ArgumentParser()
    for x in ("symbol", "source-dir", "receipt-dir", "run-id", "head-sha"):
        p.add_argument("--" + x, required=True)
    p.add_argument("--artifact-id", type=int, required=True)
    p.add_argument("--report-dir", default="output/single_stock")
    a = p.parse_args()
    ev = verify_history(a.source_dir, a.receipt_dir, symbol=a.symbol,
                        run_id=a.run_id, head_sha=a.head_sha,
                        artifact_id=a.artifact_id)
    print(json.dumps(attach_to_report(report_dir=a.report_dir, evidence=ev,
                                      symbol=a.symbol), ensure_ascii=False))


if __name__ == "__main__":
    main()
