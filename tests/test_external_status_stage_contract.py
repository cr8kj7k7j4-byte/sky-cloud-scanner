from pathlib import Path


def test_external_status_uses_canonical_w4_stage():
    workflow = Path(".github/workflows/publish-external-status-snapshot.yml").read_text(encoding="utf-8")
    assert 'status = dash.get("stage") or dash.get("status") or "UNKNOWN"' in workflow
    assert 'obs = (dash.get("sample_sufficiency") or {}).get("observed") or {}' in workflow
    assert "Preserve refreshed snapshot as immutable run artifact" in workflow
    assert "for attempt in 1 2 3 4" in workflow
