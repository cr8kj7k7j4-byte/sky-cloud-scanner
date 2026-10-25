from research.audit_sector_change_source_coverage import audit_registry

def test_sector_source_registry_blocks_unverified_exchange_years():
    registry={
        "governed_window_start":"2023-01-01",
        "exchanges":{
            "TWSE":{"years":{
                "2023":{"status":"VERIFIED","source_url":"x"},
                "2024":{"status":"UNRESOLVED"},
            }},
            "TPEx":{"years":{
                "2023":{"status":"VERIFIED","source_url":"y"},
                "2024":{"status":"VERIFIED","source_url":"z"},
            }},
        },
    }
    out=audit_registry(registry)
    assert out["status"]=="BLOCKED"
    assert out["coverage"]==0.75
    assert out["gaps"][0]["exchange"]=="TWSE"
    assert out["gaps"][0]["year"]==2024

def test_sector_source_registry_passes_only_when_all_exchange_years_verified():
    registry={
        "governed_window_start":"2023-01-01",
        "exchanges":{
            "TWSE":{"years":{
                "2023":{"status":"VERIFIED","source_url":"x"},
                "2024":{"status":"VERIFIED","source_url":"x2"},
            }},
            "TPEx":{"years":{
                "2023":{"status":"VERIFIED","source_url":"y"},
                "2024":{"status":"VERIFIED_SOURCE_URL_PENDING_PARSER","source_url":"z"},
            }},
        },
    }
    out=audit_registry(registry)
    assert out["status"]=="PASS"
    assert out["coverage"]==1.0
