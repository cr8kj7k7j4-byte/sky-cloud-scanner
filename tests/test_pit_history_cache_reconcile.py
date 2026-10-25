from __future__ import annotations

import json
from pathlib import Path

from research.reconcile_pit_history_cache import reconcile_cache


def _pit(path: Path):
    path.write_text(json.dumps({
        "intervals":[
            {
                "symbol":"1111","exchange":"TWSE","name":"A",
                "listed_from":"2023-01-01","listed_to":None,
                "source":"official",
            },
            {
                "symbol":"2222","exchange":"TPEx","name":"B",
                "listed_from":"2024-01-01","listed_to":None,
                "source":"official",
            },
        ]
    }),encoding="utf-8")


def _hist(root: Path,exchange: str,symbol: str,rows: list[dict],name="chunk_5m.json"):
    p=root/exchange/symbol/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps({
        "symbol":symbol,"exchange":exchange,"data":rows,
    }),encoding="utf-8")
    return p


def test_reconcile_drops_stale_symbols_and_out_of_membership_bars(tmp_path):
    pit=tmp_path/"pit.json";_pit(pit)
    legacy=tmp_path/"legacy"
    _hist(legacy,"TWSE","1111",[
        {"date":"2022-12-30T09:00:00+08:00","close":9.0},
        {"date":"2023-01-03T09:00:00+08:00","close":10.0},
    ])
    _hist(legacy,"TPEx","9999",[
        {"date":"2023-01-03T09:00:00+08:00","close":20.0},
    ])
    out=tmp_path/"out"
    report=reconcile_cache(
        pit_intervals=str(pit),legacy_root=str(legacy),out_root=str(out),
        from_date="2023-01-01",to_date="2026-10-22",
        source_run_id=1,source_artifact_id=2,
    )
    assert report["status"]=="PASS"
    assert report["stale_source_files_dropped"]==1
    assert report["bars_dropped_outside_corrected_membership"]==1
    assert report["bars_kept"]==1
    payload=json.loads(next(out.rglob("1111/*.json")).read_text())
    assert len(payload["data"])==1
    assert payload["data"][0]["close"]==10.0
    assert payload["source_lineage"]["reconciled_against_corrected_pit"] is True


def test_reconcile_dedupes_identical_bars(tmp_path):
    pit=tmp_path/"pit.json";_pit(pit)
    legacy=tmp_path/"legacy"
    row={"date":"2023-01-03T09:00:00+08:00","close":10.0}
    _hist(legacy,"TWSE","1111",[row],"a_5m.json")
    _hist(legacy,"TWSE","1111",[row],"b_5m.json")
    report=reconcile_cache(
        pit_intervals=str(pit),legacy_root=str(legacy),out_root=str(tmp_path/"out"),
        from_date="2023-01-01",to_date="2026-10-22",
    )
    assert report["status"]=="PASS"
    assert report["duplicate_bar_count"]==1
    assert report["conflicting_duplicate_count"]==0
    assert report["bars_kept"]==1


def test_reconcile_fails_on_conflicting_duplicate_timestamp(tmp_path):
    pit=tmp_path/"pit.json";_pit(pit)
    legacy=tmp_path/"legacy"
    _hist(legacy,"TWSE","1111",[
        {"date":"2023-01-03T09:00:00+08:00","close":10.0},
    ],"a_5m.json")
    _hist(legacy,"TWSE","1111",[
        {"date":"2023-01-03T09:00:00+08:00","close":11.0},
    ],"b_5m.json")
    report=reconcile_cache(
        pit_intervals=str(pit),legacy_root=str(legacy),out_root=str(tmp_path/"out"),
        from_date="2023-01-01",to_date="2026-10-22",
    )
    assert report["status"]=="FAIL"
    assert report["reason"]=="CONFLICTING_DUPLICATE_BARS"
    assert len(report["conflicts"])==1
