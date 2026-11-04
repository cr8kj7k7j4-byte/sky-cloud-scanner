from research.probe_swing_ca_sources import summarize


def test_schema_does_not_claim_completeness():
    x=summarize("TWSE_EXRIGHT_REFERENCE",{"stat":"OK","tables":[{"fields":["股票代號"],"data":[["2330"]]}]})
    assert x["has_records"] is True
    assert x["table_count"] == 1


def test_empty_official_response_is_not_proof_of_no_events():
    x=summarize("TPEX_EXRIGHT_REFERENCE",{"stat":"ok","data":[]})
    assert x["has_records"] is False
    assert x["data_count"] == 0


def test_twse_response_range_cannot_be_assumed_complete():
    x=summarize(
        "TWSE_EXRIGHT_REFERENCE",
        {"stat":"OK","strDate":"20261104","endDate":"20261104","data":[["115年11月04日","8467"]]},
    )
    assert x["source_range_verified"] is False
    assert x["source_range"]["reported_start"] == "20261104"
