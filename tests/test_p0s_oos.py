import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.backtest_p0s_breakout_oos import scan_file, metrics


def test_p0s_oos_synthetic(tmp_path):
    bars = []
    base = [
        ("09:00", 10.0, 10.10, 10.00, 10.00),
        ("09:05", 10.0, 10.15, 10.00, 10.05),
        ("09:10", 10.05, 10.20, 10.00, 10.10),
        ("09:15", 10.10, 10.18, 10.00, 10.12),
        ("09:20", 10.15, 10.35, 10.10, 10.30),
        ("09:25", 10.30, 11.05, 10.25, 10.95),
    ]
    for t, o, h, l, c in base:
        bars.append({
            "date": f"2026-01-02T{t}:00+08:00",
            "open": o, "high": h, "low": l, "close": c,
            "volume": 1000, "average": 9.95,
        })
    p = tmp_path / "2409_5.json"
    p.write_text(json.dumps({"symbol": "2409", "data": bars}), encoding="utf-8")
    rows = scan_file(p, cost_pct=0.0)
    assert len(rows) == 1
    assert rows[0]["entry"] == 10.2
    assert rows[0]["max_entry"] == 10.25
    assert rows[0]["target"] == 10.6
    assert rows[0]["net_r"] > 0
    m = metrics(rows)
    assert m["n"] == 1
