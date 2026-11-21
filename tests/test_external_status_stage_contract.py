from pathlib import Path


def test_external_status_uses_readonly_artifact_without_main_push():
    workflow = Path(".github/workflows/publish-external-status-snapshot.yml").read_text(encoding="utf-8")
    assert 'status = dash.get("stage") or dash.get("status") or "UNKNOWN"' in workflow
    assert 'obs = (dash.get("sample_sufficiency") or {}).get("observed") or {}' in workflow
    assert "Preserve refreshed snapshot as immutable run artifact" in workflow
    assert "contents: read" in workflow
    assert "contents: write" not in workflow
    assert "git push origin HEAD:main" not in workflow
    assert "git commit -m" not in workflow
