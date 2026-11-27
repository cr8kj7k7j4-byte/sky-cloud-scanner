"""Read existing verified Sky scan artifact for SKY維持率 price-only research.

No Fugle market API, margin-ratio inference, orders or Production authorization.
The historical label SKY維持率 does not imply actual margin-maintenance data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from research.sky_alert_reader import consume
from scripts.sky_alert_chat_readback import REPO, select_source, find_source_json
from src.sky_margin_trigger_receipt import make_receipt

TPE = ZoneInfo("Asia/Taipei")
SCHEMA = "SKY_MARGIN_EXISTING_A1_PRICE_OBSERVATION_V1"


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def build(report: dict, *, now: datetime, source: dict) -> dict:
    """Return a bounded source-dated observation, never a live A2 margin screen."""
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("OBSERVATION_TIME_REQUIRED")
    # consume independently checks official universe identity and row integrity.
    inspected = consume(report, now=now)
    rows = (inspected.get("report") or {}).get("all_symbols") or []
    checked = datetime.fromisoformat(report["checked_at_tpe"])
    if checked.utcoffset() is None:
        raise ValueError("SOURCE_TIMEZONE_REQUIRED")
    observed_date = checked.astimezone(TPE).date()
    selected = []
    for row in rows:
        if (not isinstance(row, dict)
                or row.get("source") != "Fugle paid bulk snapshot"
                or row.get("exchange") not in ("TWSE", "TPEx")
                or row.get("snapshot_is_trial") is True):
            continue
        price = _number(row.get("last_price"))
        if price is None or not (0 < price < 100):
            continue
        try:
            provider_day = date.fromisoformat(row["snapshot_source_date"])
        except (ValueError, TypeError, KeyError):
            continue
        if not observed_date - timedelta(days=7) <= provider_day <= observed_date:
            continue
        change = _number(row.get("change_pct"))
        selected.append((provider_day, change, {
            "symbol": str(row.get("symbol") or ""),
            "name": str(row.get("name") or ""),
            "exchange": row["exchange"],
            "provider_snapshot_date": provider_day.isoformat(),
            "observed_price_not_live": price,
            "observed_change_pct_not_signal": change,
            "reported_volume_raw": row.get("volume"),
            "volume_unit_verified": False,
            "executed_trade_verified": False,
            "margin_maintenance_ratio_verified": False,
            "classification": "未分級（價格研究）",
            "action": "觀察",
            "production_eligible": False,
        }))
    if selected:
        newest = max(day for day, _, _ in selected)
        selected = [item for day, change, item in selected if day == newest and item["symbol"]]
        selected.sort(key=lambda item: (
            item["observed_change_pct_not_signal"] is None,
            -(item["observed_change_pct_not_signal"] or 0),
            item["symbol"]
        ))
    else:
        newest = None
        selected = []
    return {
        "schema": SCHEMA,
        "command": "SKY維持率",
        "status": "DATED_A1_PRICE_RESEARCH_ONLY" if selected
                  else "HOLD_NO_RECENT_DATED_OBSERVATIONS",
        "read_at_tpe": now.astimezone(TPE).isoformat(),
        "source_checked_at_tpe": checked.astimezone(TPE).isoformat(),
        "source_run_id": source.get("source_run_id"),
        "source_head_sha": source.get("source_head_sha"),
        "source_artifact_id": source.get("source_artifact_id"),
        "source_json_sha256": source.get("source_json_sha256"),
        "source_freshness_status": inspected["freshness_status"],
        "provider_snapshot_date": newest.isoformat() if newest else None,
        "official_universe_count": report.get("universe_count"),
        "observed_price_count": report.get("observed_price_count"),
        "price_below_100_observation_count": len(selected),
        "preview": selected[:10],
        "sort": "OBSERVED_CHANGE_DESC_NOT_MODEL_SCORE",
        "source_date_official_session_certified": False,
        "fugle_a2_verified": False,
        "margin_ratio_screened": False,
        "volume_unit_verified": False,
        "real_margin_scan_verified": False,
        "production_eligible": False,
        "automatic_order": False,
        "trade_action": "禁止交易",
    }


def run(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)
    run_id = os.environ["GITHUB_RUN_ID"]
    sha = os.environ["GITHUB_SHA"]
    attempt = os.environ["GITHUB_RUN_ATTEMPT"]
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    # Reuse the strict OWNER/#363/exact command identity check; no credentials or
    # holdings enter a GitHub issue.
    make_receipt(event, repo=os.environ["GITHUB_REPOSITORY"], run_id=run_id,
                 attempt=attempt, sha=sha)
    result = {
        "schema": SCHEMA, "command": "SKY維持率",
        "status": "HOLD_SOURCE_ARTIFACT_UNAVAILABLE",
        "run_id": run_id, "head_sha": sha, "run_attempt": attempt,
        "real_margin_scan_verified": False,
        "production_eligible": False, "automatic_order": False,
        "trade_action": "禁止交易",
    }
    try:
        source_run, artifact = select_source(current_run_id=run_id)
        origin = str(source_run["id"])
        target = Path("/tmp/sky-margin-existing-source")
        target.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "gh", "run", "download", origin, "--repo", REPO,
            "--name", artifact["name"], "--dir", str(target)
        ], check=True)
        path = find_source_json(target)
        raw = path.read_bytes()
        source = {
            "source_run_id": origin, "source_head_sha": source_run["head_sha"],
            "source_artifact_id": int(artifact["id"]),
            "source_json_sha256": hashlib.sha256(raw).hexdigest(),
        }
        result.update(build(json.loads(raw), now=datetime.now(TPE), source=source))
        result.update(run_id=run_id, head_sha=sha, run_attempt=attempt)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        result["status"] = "HOLD_SOURCE_ARTIFACT_UNAVAILABLE"
        result["error_type"] = type(exc).__name__
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("SKY_MARGIN_EXISTING_A1_READBACK", result["status"],
          "SOURCE_RUN", result.get("source_run_id", "NONE"))


if __name__ == "__main__":
    run()
