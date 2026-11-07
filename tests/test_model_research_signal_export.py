from research.export_model_research_signals import collect


def scan(gate="PASS_FULL_MARKET_LIVE", quote_source="Fugle bulk snapshot"):
    return {
        "run_time": "2026-11-09T09:15:00+08:00",
        "market_data_gate": gate,
        "market_quote_provider": quote_source,
        "deep": [{
            "symbol": "2330", "name": "測試標的", "exchange": "TWSE",
            "last": 900, "quote_source": quote_source,
            "quote_date": "2026-11-09", "quote_time": "09:14:50",
            "ml": {"models": [
                {"model": "RF_BASELINE", "expected_return_pct": 0.5},
                {"model": "XGB_BASELINE", "expected_return_pct": -0.3},
                {"model": "NN_BASELINE", "expected_return_pct": 0},
            ]},
        }],
    }


def test_observations_keep_model_provenance_and_do_not_authorize_orders():
    result = collect(scan(), source_run_id="12", source_sha="abcdef")
    assert result["record_count"] == 3
    assert result["observed_model_ids"] == [
        "NN_BASELINE", "RF_BASELINE", "XGB_BASELINE"]
    assert [r["direction"] for r in result["records"]] == ["偏多", "偏空", "中性"]
    assert all(r["reference_executed_price"] == 900 for r in result["records"])
    assert all(r["entry_trigger"] is None and r["stop"] is None for r in result["records"])
    assert all(not r["production_eligible"] and not r["execution_authorized"] for r in result["records"])
    again = collect(scan(), source_run_id="12", source_sha="abcdef")
    assert [r["record_id"] for r in result["records"]] == [r["record_id"] for r in again["records"]]


def test_blocked_market_does_not_create_actionable_prices():
    r = collect(scan("BLOCKED_EXTERNAL_DATA_NO_TRADE"), source_run_id="12", source_sha="abc")
    assert r["record_count"] == 3
    assert all(x["reference_executed_price"] is None and x["direction"] == "待確認"
               for x in r["records"])
    assert all(x["status"] == "INSUFFICIENT_EXECUTION_EVIDENCE" for x in r["records"])


def test_mis_not_misrepresented_as_fugle_primary():
    r = collect(scan(quote_source="TWSE MIS"), source_run_id="12", source_sha="abc")
    assert all(x["reference_executed_price"] is None for x in r["records"])


def test_absent_models_are_not_fabricated():
    r = collect({"run_time": "2026-11-09T09:15:00+08:00", "deep": []},
                source_run_id="12", source_sha="abc")
    assert r["records"] == []
    assert r["status"] == "NO_VERIFIABLE_MODEL_OBSERVATIONS"


def test_unregistered_model_is_not_mislabeled_as_existing_ai():
    source = scan()
    source["deep"][0]["ml"]["models"].append({
        "model": "MODEL_4", "expected_return_pct": 999})
    r = collect(source, source_run_id="12", source_sha="abc")
    assert r["record_count"] == 3
