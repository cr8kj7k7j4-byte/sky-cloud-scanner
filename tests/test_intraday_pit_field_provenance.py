from research.audit_intraday_pit_field_provenance import audit_registry

def test_field_provenance_blocks_missing_frozen_sources():
    out=audit_registry({
        "domains":{
            "pit":{"status":"PASS","fields":["pit_universe_member"]},
            "phase":{"status":"BLOCKED","fields":["phase"],"required_source":"FROZEN"},
        }
    })
    assert out["status"]=="DATA_BLOCKED"
    assert "phase" in out["blocking_domains"]

def test_field_provenance_passes_only_when_all_domains_ready():
    out=audit_registry({
        "domains":{
            "pit":{"status":"PASS","fields":["a"]},
            "market":{"status":"ENGINE_READY","fields":["b"]},
        }
    })
    assert out["status"]=="PASS"
    assert out["engine/source_ready_share"]==1.0
