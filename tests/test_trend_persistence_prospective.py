from research.trend_persistence_prospective import _ecdf, score_events, build_dashboard


def test_ecdf_uses_count_lte_over_n():
    xs = [1.0, 2.0, 2.0, 4.0]
    assert _ecdf(xs, 1.0) == 0.25
    assert _ecdf(xs, 2.0) == 0.75
    assert _ecdf(xs, 4.0) == 1.0


def _event(symbol, x):
    return {
        "symbol": symbol,
        "breadth": 0.60,
        "breadth_delta5": 0.01,
        "rs_pct": x,
        "rs_delta5": x / 10,
        "volume_ratio20": 1 + x,
        "ret5": x / 100,
        "ret20": x / 50,
        "distance_ma20": 0.08 - x / 100,
        "range_pct": 0.08 - x / 100,
        "realized_vol20": 0.08 - x / 100,
        "gap_abs": 0.08 - x / 100,
    }


def test_score_is_equal_weight_and_top_decile_includes_ties():
    events = [_event(str(i), i / 10) for i in range(1, 11)]
    scored = score_events(events)
    assert len(scored) == 10
    selected = [x for x in scored if x["selected"]]
    assert selected
    assert all(x["score_pct"] >= 0.90 for x in selected)


def test_dashboard_waits_before_sufficiency():
    state = {
        "snapshots": {
            "2026-10-28": {},
            "2026-10-29": {},
        },
        "signals": [],
    }
    d = build_dashboard(state)
    assert d["decision"] == "WAITING_FOR_SUFFICIENCY"
    assert d["production_change"] is False
    assert d["regime_gate"] == "DATA_BLOCKED"


def test_dashboard_rejects_after_sufficiency_when_cost_edge_fails():
    snapshots = {}
    # 25 prospective market dates.
    for day in range(1, 26):
        snapshots[f"2026-11-{day:02d}"] = {}
    signals = []
    # 200 evaluated, deliberately negative after cost.
    for i in range(200):
        signals.append({
            "signal_date": "2026-11-01",
            "symbol": f"{1000 + (i % 50)}",
            "status": "EVALUATED",
            "net_045": -0.001,
            "net_065": -0.003,
        })
    state = {"snapshots": snapshots, "signals": signals}
    d = build_dashboard(state)
    assert d["sufficiency_pass"] is True
    assert d["decision"] == "REJECT_CANDIDATE"
