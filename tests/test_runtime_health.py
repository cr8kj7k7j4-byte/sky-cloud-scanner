from src.runtime_health import health_payload, readiness_payload

def test_health_ok():
    assert health_payload()["status"] == "ok"

def test_readiness_fails_on_source_health():
    r = readiness_payload(source_health={"twse":{"ok":True},"tpex":{"ok":False}}, state_health={"ok":True})
    assert r["ready"] is False
    assert "tpex" in r["failed_sources"]
