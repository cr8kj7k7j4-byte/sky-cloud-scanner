from pathlib import Path

from src.execution_calibration_ledger import (
    ExecutionCalibrationSample,
    append_sample,
    load_samples,
    summarize_calibration,
)


def test_calibration_rates_and_private_storage(tmp_path):
    p = tmp_path / "private" / "ledger.csv"
    sample = ExecutionCalibrationSample(
        trade_date="2026-10-24",
        transaction_mode="CASH_DAYTRADE",
        shares=1000,
        buy_price=50.0,
        sell_price=51.0,
        buy_commission_twd=17,
        sell_commission_twd=17,
        sell_tax_twd=77,
    )
    append_sample(sample, p)
    rows = load_samples(p)
    assert len(rows) == 1
    assert rows[0].buy_commission_rate > 0
    assert rows[0].sell_tax_rate > 0


def test_slippage_requires_expected_prices():
    sample = ExecutionCalibrationSample(
        trade_date="2026-10-24",
        transaction_mode="CASH_DAYTRADE",
        shares=1000,
        buy_price=50,
        sell_price=51,
        buy_commission_twd=17,
        sell_commission_twd=17,
        sell_tax_twd=77,
    )
    assert sample.entry_slippage_bps is None
    assert sample.exit_slippage_bps is None


def test_summary_does_not_claim_ready_on_two_samples():
    samples = [
        ExecutionCalibrationSample("2026-10-24","CASH_DAYTRADE",1000,50,51,17,17,77),
        ExecutionCalibrationSample("2026-10-24","MARGIN_FINANCING",1000,50,51,17,17,153,8),
    ]
    out = summarize_calibration(samples)
    assert out["sample_count"] == 2
    assert out["status"] == "EARLY_SAMPLE"
    assert out["entry_slippage_bps_median"] is None
