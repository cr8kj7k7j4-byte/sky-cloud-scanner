from __future__ import annotations

import json

from research.audit_pit_intraday_history import audit
from research.build_pit_history_manifest import build_manifest


def test_pit_history_manifest_includes_delisted_members_not_current_only():
    intervals=[
        {
            "symbol":"1111","exchange":"TWSE","name":"Old",
            "listed_from":"2020-01-01","listed_to":"2024-06-30","source":"official",
        },
        {
            "symbol":"2222","exchange":"TWSE","name":"Current",
            "listed_from":"2025-01-01","listed_to":None,"source":"official",
        },
    ]
    m=build_manifest(intervals,from_date="2023-01-01",to_date="2026-10-25")
    assert m["symbol_count"]==2
    assert m["survivorship_bias_warning"] is None
    old=next(x for x in m["sample"] if x["symbol"]=="1111")
    assert old["history_required_to"]=="2024-06-30"


def test_pit_history_audit_uses_symbol_day_coverage(tmp_path):
    manifest={
        "method":"pit",
        "sample":[
            {"symbol":"1111","exchange":"TWSE","history_required_from":"2026-01-05","history_required_to":"2026-01-06"},
            {"symbol":"2222","exchange":"TWSE","history_required_from":"2026-01-05","history_required_to":"2026-01-06"},
        ],
    }
    for sym in ("1111","2222"):
        rows=[
            {"date":"2026-01-05T09:00:00+08:00","open":10,"high":10,"low":10,"close":10,"volume":1,"average":10},
            {"date":"2026-01-06T09:00:00+08:00","open":10,"high":10,"low":10,"close":10,"volume":1,"average":10},
        ]
        (tmp_path/f"{sym}_5.json").write_text(
            json.dumps({"symbol":sym,"data":rows}),encoding="utf-8"
        )
    report=audit(manifest,str(tmp_path),[])
    assert report["status"]=="PASS"
    assert report["symbol_day_coverage"]==1.0


def test_pit_history_audit_fails_below_95_percent(tmp_path):
    manifest={
        "method":"pit",
        "sample":[
            {"symbol":"1111","exchange":"TWSE","history_required_from":"2026-01-05","history_required_to":"2026-01-05"},
            {"symbol":"2222","exchange":"TWSE","history_required_from":"2026-01-05","history_required_to":"2026-01-05"},
        ],
    }
    (tmp_path/"1111_5.json").write_text(json.dumps({
        "symbol":"1111","data":[{"date":"2026-01-05T09:00:00+08:00"}]
    }),encoding="utf-8")
    report=audit(manifest,str(tmp_path),[])
    assert report["status"]=="FAIL"
    assert report["symbol_day_coverage"]==0.5
