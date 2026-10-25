from src.mobile_api import build_mobile_payload, validate_mobile_payload

def test_mobile_contract_has_required_fields():
    p = build_mobile_payload({"symbol":"2409","last":37.1,"monitor":{"action":"等待"}}, timestamp="2026-10-25T09:30:00+08:00", data_quality_status="HEALTHY")
    v = validate_mobile_payload(p)
    assert v["valid_contract"] is True
    assert p["action"] == "等待"
    assert v["decision_logic_owned_here"] is False
