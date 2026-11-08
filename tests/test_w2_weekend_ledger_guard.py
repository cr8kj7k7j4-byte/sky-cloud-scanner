"""W2 weekend ledger must never query paid Fugle or write GCS."""
from datetime import date
from pathlib import Path
from unittest.mock import patch

from research.three_model_fugle_pipeline import run


def test_weekend_ledger_skips_without_provider_or_gcs(tmp_path):
    output = tmp_path / "weekend.json"
    with patch("research.three_model_fugle_pipeline.read_fugle", side_effect=AssertionError("paid API called")):
        result = run(["1101", "8088"], date(2026, 11, 8), "private-test-bucket",
                     "three-model-research/v1", "unused", object(), output)
    assert result["status"] == "SKIPPED_NO_COMPLETED_WEEKEND_SESSION"
    assert result["saved_records"] == 0
    assert result["provider_authenticated"] is False
    assert result["production_signal"] is False
    assert output.exists()
