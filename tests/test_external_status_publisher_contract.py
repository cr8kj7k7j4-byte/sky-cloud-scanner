from pathlib import Path


WORKFLOW = Path(".github/workflows/publish-external-status-snapshot.yml")


def test_external_status_publisher_retains_artifact_and_fails_visibly():
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "Upload latest status snapshot artifact" in content
    assert "if: always()" in content
    assert "git push origin HEAD:main" in content
    assert "for attempt in 1 2 3" in content
    assert "exit 1" in content
    assert "git fetch origin main" in content


def test_external_status_uses_canonical_w4_stage_not_legacy_status():
    content = WORKFLOW.read_text(encoding="utf-8")
    assert 'status = dash.get("stage") or dash.get("status") or "UNKNOWN"' in content
    assert 'obs = (dash.get("sample_sufficiency") or {}).get("observed") or {}' in content
