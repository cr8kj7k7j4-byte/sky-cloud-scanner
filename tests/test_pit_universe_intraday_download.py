import json
from pathlib import Path

from research.download_pit_universe_intraday import (
    build_manifest,
    load_pit_union,
)


def test_load_pit_union_includes_any_symbol_active_in_window(tmp_path):
    p = tmp_path / "pit.json"
    p.write_text(json.dumps({
        "intervals": [
            {"symbol": "1111", "exchange": "TWSE", "listed_from": "2023-01-01", "listed_to": None},
            {"symbol": "2222", "exchange": "TPEx", "listed_from": "2024-01-01", "listed_to": "2025-01-31"},
            {"symbol": "3333", "exchange": "TWSE", "listed_from": "2020-01-01", "listed_to": "2022-12-31"},
        ]
    }), encoding="utf-8")
    out = load_pit_union(str(p), "2023-05-23", "2026-10-22")
    assert [(x["exchange"], x["symbol"]) for x in out] == [
        ("TPEx", "2222"),
        ("TWSE", "1111"),
    ]


def test_manifest_counts_exchanges():
    items = [
        {"symbol": "1111", "exchange": "TWSE", "listed_from": "2023-01-01", "listed_to": None},
        {"symbol": "2222", "exchange": "TPEx", "listed_from": "2023-01-01", "listed_to": None},
        {"symbol": "3333", "exchange": "TWSE", "listed_from": "2023-01-01", "listed_to": None},
    ]
    out = build_manifest(items, "2023-05-23", "2026-10-22")
    assert out["symbol_count"] == 3
    assert out["twse_count"] == 2
    assert out["tpex_count"] == 1
    assert out["universe_method"] == "PIT_INTERVAL_UNION"
