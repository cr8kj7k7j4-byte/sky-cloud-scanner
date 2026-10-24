from src.outcome_engine import evaluate_long_outcome
from src.walk_forward import generate_walk_forward_folds, validate_no_overlap, chronological_split
from src.trade_log import build_trade_decision_record, attach_outcome


def test_outcome_calculates_mfe_mae_and_r():
    bars=[
        {"high":101.0,"low":99.5,"close":100.5},
        {"high":104.0,"low":100.0,"close":103.0},
        {"high":103.5,"low":101.5,"close":102.0},
    ]
    out=evaluate_long_outcome(entry=100,stop=98,target=104,bars=bars,exit_price=102,fee_rate=0.0,tax_rate=0.0,slippage_rate=0.0)
    p=out.to_dict()
    assert p["status"]=="COMPLETE"
    assert p["mfe_pct"]==4.0
    assert p["mae_pct"]==-0.5
    assert p["r_multiple"]==1.0
    assert p["hit_target"] is True
    assert p["hit_stop"] is False


def test_outcome_includes_costs():
    bars=[{"high":101.0,"low":99.0,"close":100.5}]
    out=evaluate_long_outcome(entry=100,stop=99,target=103,bars=bars,exit_price=100.5,fee_rate=0.001,tax_rate=0.001,slippage_rate=0.001)
    assert out.net_pnl < out.gross_pnl


def test_walk_forward_folds_do_not_overlap():
    folds=generate_walk_forward_folds("2021-01-01","2025-12-31",train_days=365,validate_days=90,test_days=90,step_days=90)
    assert len(folds) > 0
    assert all(validate_no_overlap(f) for f in folds)


def test_chronological_split_preserves_order():
    rows=[{"observed_at":"2026-01-03"},{"observed_at":"2026-01-01"},{"observed_at":"2026-01-02"},{"observed_at":"2026-01-04"},{"observed_at":"2026-01-05"}]
    s=chronological_split(rows,train_ratio=0.6,validate_ratio=0.2)
    assert [x["observed_at"] for x in s["train"]] == ["2026-01-01","2026-01-02","2026-01-03"]
    assert [x["observed_at"] for x in s["validate"]] == ["2026-01-04"]
    assert [x["observed_at"] for x in s["test"]] == ["2026-01-05"]


def test_outcome_attaches_to_decision_ledger():
    rec=build_trade_decision_record(
        item={"symbol":"2409","name":"友達","risk":{"status":"BLOCK"}},
        run_id="run-1",
    )
    out=evaluate_long_outcome(
        entry=100,stop=98,target=104,
        bars=[{"high":102,"low":99,"close":101}],
        exit_price=101,
    )
    payload=attach_outcome(rec,out)
    assert payload["outcome"]["status"]=="COMPLETE"
    assert payload["outcome"]["r_multiple"]==0.5
