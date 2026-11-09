"""Paid Fugle TSE+OTC routing cannot depend on free MIS fallback."""
from src.quote_provider import select_certified_candidate_rows


ROWS = [{"symbol": "1101", "exchange": "TWSE"},
        {"symbol": "6182", "exchange": "TPEx"}]


def test_paid_fugle_preserves_otc_when_mis_disabled():
    source = {"provider": "Fugle bulk snapshot", "fallback_used": False,
              "rows": ROWS, "audit": {"valid_whole_market_operational": True}}
    out = select_certified_candidate_rows(source, allow_mis_otc_fallback=False)
    assert [x["symbol"] for x in out] == ["1101", "6182"]


def test_partial_unverified_fugle_never_enters_candidate_gate():
    source = {"provider": "Fugle bulk snapshot (partial research)",
              "fallback_used": False, "rows": ROWS,
              "audit": {"valid_whole_market_operational": False}}
    assert select_certified_candidate_rows(source, allow_mis_otc_fallback=False) == []


def test_mis_backup_does_not_promote_otc_when_disabled():
    source = {"provider": "TWSE MIS (fallback, OTC not TPEx-certified)",
              "fallback_used": True, "rows": ROWS,
              "audit": {"valid_whole_market_operational": True}}
    assert [x["symbol"] for x in select_certified_candidate_rows(
        source, allow_mis_otc_fallback=False)] == ["1101"]


def test_lack_of_whole_market_evidence_blocks_everything():
    source = {"provider": "Fugle bulk snapshot", "fallback_used": False,
              "rows": ROWS, "audit": {}}
    assert select_certified_candidate_rows(source, allow_mis_otc_fallback=False) == []
