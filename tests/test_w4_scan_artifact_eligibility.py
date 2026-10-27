from __future__ import annotations

import json
from pathlib import Path

from research.w4_scan_artifact_eligibility import audit_scan_artifacts


def _write(root: Path, run_id: str, name: str, records):
    p=root/run_id/"output"/"paper"/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps({"records":records}),encoding="utf-8")
    return p


def test_empty_holiday_scan_is_not_eligible(tmp_path):
    root=tmp_path/"shadow_history"
    _write(root,"100","a.json",[])
    out=audit_scan_artifacts(str(root))
    assert out["run_count"]==1
    assert out["eligible_run_count"]==0
    assert out["eligible_record_count"]==0
    assert out["ineligible_or_empty_runs"]==["100"]


def test_nonempty_post_ledger_scan_is_eligible(tmp_path):
    root=tmp_path/"shadow_history"
    _write(root,"101","a.json",[
        {
            "run_id":"r1",
            "observed_at":"2026-10-27T09:05:00+08:00",
            "symbol":"2330",
        }
    ])
    out=audit_scan_artifacts(str(root))
    assert out["eligible_run_count"]==1
    assert out["eligible_record_count"]==1
    assert out["eligible_run_ids"]==["101"]


def test_pre_ledger_records_do_not_count(tmp_path):
    root=tmp_path/"shadow_history"
    _write(root,"099","a.json",[
        {
            "run_id":"old",
            "observed_at":"2026-10-24T20:00:00+08:00",
            "symbol":"2330",
        }
    ])
    out=audit_scan_artifacts(str(root))
    assert out["eligible_run_count"]==0


def test_missing_symbol_does_not_count_as_evidence(tmp_path):
    root=tmp_path/"shadow_history"
    _write(root,"102","a.json",[
        {
            "run_id":"r2",
            "observed_at":"2026-10-27T09:15:00+08:00",
            "symbol":"",
        }
    ])
    out=audit_scan_artifacts(str(root))
    assert out["eligible_run_count"]==0


def test_missing_scan_artifacts_are_not_reported_as_pass(tmp_path):
    root=tmp_path/"shadow_history"
    out=audit_scan_artifacts(str(root))
    assert out["paper_files_scanned"]==0
    assert out["eligible_run_count"]==0
    assert out["status"]=="NO_INPUT_ARTIFACTS"
    assert out["governance"]["zero_source_files_cannot_pass"] is True
