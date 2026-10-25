import csv
import json

from research.top100_velocity_baseline import (
    aggregate_and_select,
    build_shard_rows,
)


def test_build_and_aggregate_top100_velocity(tmp_path):
    root = tmp_path / "hist" / "TWSE" / "0001"
    root.mkdir(parents=True)

    bars = []

    def add(ts, o, c, v):
        bars.append({
            "date": ts,
            "open": o,
            "high": max(o, c),
            "low": min(o, c),
            "close": c,
            "volume": v,
        })

    add("2026-01-02T13:25:00+08:00", 10, 10, 100)

    h, m = 9, 0
    for i in range(16):
        total = h * 60 + m + i * 5
        hh = total // 60
        mm = total % 60
        ts = f"2026-01-05T{hh:02d}:{mm:02d}:00+08:00"
        o = 10 + 0.01 * i
        c = o + 0.01
        v = 100 + i * 10
        add(ts, o, c, v)

    (root / "x_5m.json").write_text(
        json.dumps({
            "symbol": "0001",
            "exchange": "TWSE",
            "data": bars,
        }),
        encoding="utf-8",
    )

    out = tmp_path / "s.csv"
    assert build_shard_rows(str(tmp_path / "hist"), str(out)) >= 1

    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    base = rows[0]
    shard = tmp_path / "agg.csv"
    fields = list(base.keys())

    with shard.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()

        for i in range(120):
            r = dict(base)
            r["symbol"] = f"{i:04d}"

            if i == 0:
                r["current_return"] = "0.08"
                r["prior_return"] = "0.01"
                r["price_velocity"] = "0.03"
                r["volume_accel"] = "2.0"
            else:
                r["current_return"] = str(0.079 - i * 0.0005)
                r["prior_return"] = str(0.079 - i * 0.0001)
                r["price_velocity"] = "0.001"
                r["volume_accel"] = "0.1"

            r["current_price"] = "50"
            r["gross_return_60m"] = "0.02"
            w.writerow(r)

    trades = tmp_path / "trades.csv"
    report = tmp_path / "report.json"

    rep = aggregate_and_select(
        [str(shard)],
        str(trades),
        str(report),
    )

    assert rep["trade_count"] >= 1
    assert rep["frozen_spec"]["top_pool"] == 100
    assert rep["frozen_spec"]["primary_round_trip_cost"] == 0.0045
    assert rep["frozen_spec"]["exit"] == "close after 60 minutes (12 x 5m bars)"
