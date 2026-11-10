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
    assert d["regime_gate"] == "INCOMPLETE"


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


def test_d1_open_at_or_above_100_is_rejected():
    from research.trend_persistence_prospective import evaluate_matured
    state = {
        "snapshots": {
            "2026-10-29": {"1234": {"open": 100.0, "close": 101.0}},
            "2026-10-30": {"1234": {"open": 101.0, "close": 102.0}},
            "2026-11-02": {"1234": {"open": 102.0, "close": 103.0}},
            "2026-11-03": {"1234": {"open": 103.0, "close": 104.0}},
            "2026-11-04": {"1234": {"open": 104.0, "close": 105.0}},
        },
        "signals": [{
            "signal_date": "2026-10-28",
            "symbol": "1234",
            "status": "PENDING",
            "entry_date": None,
            "entry_open": None,
            "outcome_date": None,
            "exit_close": None,
            "gross_f5": None,
            "net_045": None,
            "net_065": None,
        }],
    }
    evaluate_matured(state)
    assert state["signals"][0]["status"] == "ENTRY_REJECTED_PRICE"
    assert state["signals"][0]["entry_open"] == 100.0


def test_regime_uses_taiex_ma60_and_20d_slope():
    from research.trend_persistence_prospective import regime_for_date
    from datetime import date, timedelta
    benchmark = {}
    d = date(2026, 1, 1)
    # 100 monotonically rising synthetic benchmark observations.
    for i in range(100):
        benchmark[(d + timedelta(days=i)).isoformat()] = 10000.0 + i * 10.0
    last = (d + timedelta(days=99)).isoformat()
    assert regime_for_date(benchmark, last) == "BULL"


def test_dashboard_requires_two_known_regimes_for_regime_coverage():
    state = {"snapshots": {}, "signals": []}
    for day in range(1, 26):
        state["snapshots"][f"2026-11-{day:02d}"] = {}
    for i in range(200):
        state["signals"].append({
            "signal_date": "2026-11-01",
            "symbol": f"{1000 + (i % 50)}",
            "status": "EVALUATED",
            "net_045": 0.01 if i % 5 else -0.002,
            "net_065": 0.008 if i % 5 else -0.003,
            "regime": "BULL",
        })
    d = build_dashboard(state)
    assert d["sufficiency_pass"] is True
    assert d["regime_gate"] == "INCOMPLETE"
    assert d["decision"] == "HOLD_REGIME_COVERAGE_INCOMPLETE"


def test_blocked_provider_writes_diagnostic_without_state(tmp_path, monkeypatch):
    import json
    import sys
    import pytest
    import research.trend_persistence_prospective as module

    def blocked(*args, **kwargs):
        raise PermissionError("FREE_MIS_MARKETDATA_DISABLED_BY_USER_POLICY")

    monkeypatch.setattr(module, "run", blocked)
    monkeypatch.setattr(sys, "argv", ["trend", "--history-dir", "unused",
                                     "--out", str(tmp_path)])
    with pytest.raises(PermissionError):
        module.main()
    result = json.loads((tmp_path / "failure.json").read_text())
    assert result["reason"] == "FUGLE_ONLY_LEGACY_MIS_BLOCKED"
    assert result["status"] == "DATA_BLOCKED"
    assert result["state_updated"] is False
    assert result["trade_eligible"] is False
    assert not (tmp_path / "state.json").exists()
    assert "DATA_BLOCKED" in (tmp_path / "latest.md").read_text()


def test_unexpected_failure_remains_failed_and_scrubs_error(tmp_path, monkeypatch):
    import json
    import sys
    import pytest
    import research.trend_persistence_prospective as module

    def broken(*args, **kwargs):
        raise RuntimeError("sensitive-provider-detail")

    monkeypatch.setattr(module, "run", broken)
    monkeypatch.setattr(sys, "argv", ["trend", "--history-dir", "unused",
                                     "--out", str(tmp_path)])
    with pytest.raises(RuntimeError):
        module.main()
    raw = (tmp_path / "failure.json").read_text()
    assert json.loads(raw)["reason"] == "PROSPECTIVE_UPDATE_FAILED"
    assert "sensitive-provider-detail" not in raw
    assert not (tmp_path / "state.json").exists()
