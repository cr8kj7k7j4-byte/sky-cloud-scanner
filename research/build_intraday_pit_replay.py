from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from research.intraday_replay_validator import validate_replay_frame
from src.data_quality import assess_dataframe
from src.point_in_time_universe import universe_as_of


REPLAY_SCHEMA_VERSION = "w3a-intraday-pit-replay-v1"


def _load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _membership_lookup(intervals: list[dict], dates: list[str]) -> dict[tuple[str, str], dict]:
    out = {}
    for d in sorted(set(dates)):
        for row in universe_as_of(intervals, d):
            out[(str(row["symbol"]), d)] = row
    return out


def _hash_file(path: str | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_replay(decisions: pd.DataFrame, intervals: list[dict]) -> pd.DataFrame:
    df = decisions.copy()
    if "session_date" not in df.columns:
        if "decision_timestamp" not in df.columns:
            raise ValueError("decisions require session_date or decision_timestamp")
        df["session_date"] = pd.to_datetime(
            df["decision_timestamp"], errors="coerce", utc=True
        ).dt.tz_convert("Asia/Taipei").dt.date.astype(str)

    lookup = _membership_lookup(intervals, df["session_date"].astype(str).tolist())
    pit = []
    source = []
    eff_from = []
    eff_to = []
    for row in df.to_dict("records"):
        key = (str(row.get("symbol")), str(row.get("session_date")))
        x = lookup.get(key)
        pit.append(x is not None)
        source.append(x.get("source") if x else None)
        eff_from.append(x.get("listed_from") if x else None)
        eff_to.append(x.get("listed_to") if x else None)

    df["pit_universe_member"] = pit
    df["universe_source"] = source
    df["universe_effective_from"] = eff_from
    df["universe_effective_to"] = eff_to

    if "data_quality_status" not in df.columns:
        df["data_quality_status"] = "UNKNOWN"
    if "leakage_audit_status" not in df.columns:
        df["leakage_audit_status"] = "UNKNOWN"
    if "market_context_status" not in df.columns:
        df["market_context_status"] = "UNKNOWN"
    if "sector_mapping_status" not in df.columns:
        df["sector_mapping_status"] = "UNKNOWN"
    if "execution_context_status" not in df.columns:
        df["execution_context_status"] = "UNKNOWN"
    if "replay_coverage_status" not in df.columns:
        df["replay_coverage_status"] = "UNKNOWN"

    return df


def run_pipeline(decisions_csv: str, pit_universe_json: str, out_dir: str) -> dict:
    decisions = pd.read_csv(decisions_csv)
    intervals = _load_json(pit_universe_json)
    if isinstance(intervals, dict):
        intervals = intervals.get("intervals") or intervals.get("rows") or []

    replay = build_replay(decisions, intervals)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    dataset_path = out / "intraday_pit_replay.csv"
    replay.to_csv(dataset_path, index=False)

    dq = assess_dataframe(
        replay,
        dataset="intraday_pit_replay",
        required_columns=[
            "decision_id",
            "symbol",
            "session_date",
            "decision_timestamp",
            "feature_cutoff_timestamp",
            "pit_universe_member",
        ],
        timestamp_column="decision_timestamp",
        expected_rows=len(decisions),
        source_health="PASS",
    )
    contract = validate_replay_frame(replay)

    manifest = {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "row_count": int(len(replay)),
        "symbol_count": int(replay["symbol"].astype(str).nunique()) if "symbol" in replay else 0,
        "session_start": str(replay["session_date"].min()) if len(replay) else None,
        "session_end": str(replay["session_date"].max()) if len(replay) else None,
        "research_split_counts": replay.get("research_split", pd.Series(dtype=str))
            .astype(str).value_counts().to_dict(),
        "inputs": {
            "decisions_csv": decisions_csv,
            "decisions_sha256": _hash_file(decisions_csv),
            "pit_universe_json": pit_universe_json,
            "pit_universe_sha256": _hash_file(pit_universe_json),
        },
        "dq": dq,
        "w2_contract": contract,
        "status": "PASS" if contract["gate"] == "PASS" else "DATA_BLOCKED",
        "production_change": False,
    }

    (out / "intraday_pit_replay_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "intraday_pit_replay_gap_report.json").write_text(
        json.dumps(
            {
                "status": manifest["status"],
                "reasons": contract["reasons"],
                "context_coverage": contract["context_coverage"],
                "outcome_coverage": contract["outcome_coverage"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--pit-universe", required=True)
    ap.add_argument("--out-dir", default="research_output/w3a_intraday_pit")
    args = ap.parse_args()
    result = run_pipeline(args.decisions, args.pit_universe, args.out_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
