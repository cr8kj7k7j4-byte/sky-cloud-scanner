from src.feature_parity import compare_feature_contracts

BASE = {
    "momentum_1": {
        "formula": "x",
        "version": "1.0.0",
        "timestamp_semantics": "pit",
        "normalization": "none",
        "missing_policy": "NULL",
    }
}

def test_parity_pass():
    out = compare_feature_contracts(BASE, BASE, universe_equal=True)
    assert out["status"] == "PASS"

def test_parity_fail_formula():
    online = {"momentum_1": dict(BASE["momentum_1"], formula="changed")}
    out = compare_feature_contracts(BASE, online, universe_equal=True)
    assert out["status"] == "PARITY_FAIL"
    assert "formula" in out["mismatches"]["momentum_1"]

def test_parity_fail_universe():
    out = compare_feature_contracts(BASE, BASE, universe_equal=False)
    assert out["status"] == "PARITY_FAIL"
