from research.audit_swing_pit_price_coverage import compress_missing


def test_missingness_is_not_forward_filled():
    out = compress_missing(["2024-01-02", "2024-01-03", "2024-02-01"])
    assert out[0]["month"] == "2024-01"
    assert out[0]["missing_days"] == 2
    assert "NO_BAR_NO_FORWARD_FILL" in out[0]["reason"]
