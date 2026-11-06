"""MOPS official PIT collector smoke remains read-only on push."""
from pathlib import Path


def test_main_collector_change_runs_one_source_smoke_without_ledger_loop():
    path = Path(__file__).resolve().parents[1] / ".github/workflows/mops-revenue-pit-collector.yml"
    workflow = path.read_text(encoding="utf-8")
    before_permissions = workflow.split("\npermissions:", 1)[0]
    assert "  push:" in before_permissions
    assert "      - main" in before_permissions
    assert "      - 'research/collect_mops_revenue_pit.py'" in before_permissions
    assert "      - '.github/workflows/mops-revenue-pit-collector.yml'" in before_permissions
    assert "data/revenue_pit/" not in before_permissions
    assert "if: github.event_name == 'schedule' || (github.event_name == 'workflow_dispatch' && github.ref_name == 'main')" in workflow
