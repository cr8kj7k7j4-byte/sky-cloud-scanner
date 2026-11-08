"""Offline W3A classification audit for zero-candidate investigations."""
from src.w3a_candidate_funnel import build_candidate_funnel


def _audit(data_gate="PASS_FULL_MARKET_LIVE", **kw):
    return build_candidate_funnel(
        universe_count=1000,
        quote_audit={"valid_quote_count": 800, "quote_coverage_pct": 80.0,
                     "received_by_exchange": {"TWSE": 500, "TPEx": 400},
                     "missing_by_exchange": {"TWSE": 100, "TPEx": 0},
                     "rejected_by_exchange": {"TWSE": {}, "TPEx": {}}},
        source="Fugle bulk snapshot",
        data_gate=data_gate,
        working_count=kw.get("working_count", 800),
        first_pass=kw.get("first_pass", 60),
        top=kw.get("top", 30),
        deep=kw.get("deep", 4),
        rejected=kw.get("rejected", 1),
        unverified=kw.get("unverified", 2),
        gate_failures=kw.get("gate_failures", ["PRICE_TOO_HIGH", "VOLUME_TOO_LOW"]),
    )


def test_market_block_never_claims_absence_of_setups():
    x = _audit("BLOCKED_EXTERNAL_DATA_NO_TRADE", working_count=0,
               first_pass=0, top=0, deep=0, rejected=0, unverified=0)
    assert x["zero_candidate_diagnostic"] == "MARKET_DATA_GATE_BLOCKED"
    assert x["new_trade_approval"] is False
    assert x["valid_executed_quotes"] == 800
    assert x["missing_by_exchange"]["TWSE"] == 100


def test_first_gate_reject_all_is_not_provider_failure():
    x = _audit(first_pass=0, top=0, deep=0, rejected=0,
               unverified=0, gate_failures=["PRICE", "PRICE", "VOLUME"])
    assert x["zero_candidate_diagnostic"] == "FIRST_GATE_REJECTED_ALL"
    assert x["first_gate_reasons"] == {"PRICE": 2, "VOLUME": 1}


def test_fugle_deep_dive_permission_gap_classified_separately():
    x = _audit(deep=0, rejected=0, unverified=5)
    assert x["zero_candidate_diagnostic"] == "FUGLE_DEEP_DIVE_UNVERIFIED"


def test_all_deep_rejected_is_not_market_data_failure():
    x = _audit(deep=0, rejected=4, unverified=0)
    assert x["zero_candidate_diagnostic"] == "DEEP_DIVE_REJECTED_ALL"


def test_deep_candidates_dont_become_trade_approval():
    x = _audit(deep=3)
    assert x["zero_candidate_diagnostic"] == "DEEP_CANDIDATES_PRESENT_NOT_TRADE_APPROVAL"
    assert x["new_trade_approval"] is False
