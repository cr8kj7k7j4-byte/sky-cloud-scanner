"""W0 regression: expired timed monitors may not reactivate after 2026-11-10.

The scripts, proof, active scanners and 5-minute market dispatcher are retained.
Only obsolete schedule *entrypoints* are removed.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"

EXPIRED = (
    "sky-overnight-readiness-watch-20261109.yml",
    "sky-overnight-13col-acceptance.yml",
    "sky-overnight-readonly-acceptance-20261110.yml",
    "sky-preopen-watch-20261110.yml",
    "sky-preopen-evidence-monitor.yml",
)
PRESERVED = (
    "scan.yml",
    "sky-full-market-five-minute-dispatch.yml",
    "sky-full-market-private.yml",
    "sky-chat-bridge.yml",
    "schedule-health-audit.yml",
    "research-freeze-governance.yml",
    "sky-paper-only-acceptance.yml",
    "sky-recovery-watchdog.yml",
    "sky-research-ci-watchdog.yml",
)


def test_only_expired_overnight_workflow_entrypoints_removed():
    assert all(not (WF / f).exists() for f in EXPIRED)


def test_live_market_scan_and_governance_entrypoints_preserved():
    assert all((WF / f).is_file() for f in PRESERVED)


def test_historical_monitor_implementation_and_tests_preserved():
    assert (ROOT / "ops" / "preopen_readiness_watch.py").is_file()
    assert (ROOT / "ops" / "recovery" / "sky_overnight_readonly_acceptance.py").is_file()
    assert (ROOT / "tests" / "test_preopen_readiness_watch.py").is_file()
    assert (ROOT / "tests" / "test_archived_workflow_cleanup.py").is_file()


def test_research_and_no_broker_live_safety_preserved():
    registry = (ROOT / "SKY_SYSTEM_REGISTRY_V2_1.md").read_text(encoding="utf-8")
    policy = (ROOT / "docs" / "SKY_NO_BROKER_ACCOUNT_RESEARCH_POLICY_V1.md").read_text(encoding="utf-8")
    assert "Sky Day Trading v1.4" in registry
    assert "Sky Swing V1.0" in registry
    assert "NO_LIVE_TRADING" in policy
    assert (ROOT / "research" / "RESEARCH_FREEZE_REGISTRY.md").is_file()


def test_expired_24h_watchdog_crons_removed_but_manual_pr_tests_work():
    for name in ("sky-research-ci-watchdog.yml", "w2-research-24h-watchdog.yml"):
        content = (WF / name).read_text(encoding="utf-8")
        assert "  schedule:" not in content
        assert "*/5 * * * *" not in content
        assert "  workflow_dispatch:" in content
        assert "  pull_request:" in content


def test_no_legacy_expired_monitor_can_auto_dispatch_paid_scan():
    for name in ("sky-research-ci-watchdog.yml", "w2-research-24h-watchdog.yml"):
        content = (WF / name).read_text(encoding="utf-8")
        assert "  schedule:" not in content
    assert (WF / "scan.yml").is_file()
    assert (WF / "sky-full-market-five-minute-dispatch.yml").is_file()


def test_expired_one_shot_dual_scan_dispatch_removed():
    assert not (WF / "sky-research-once-20261109.yml").exists()
    assert (WF / "scan.yml").is_file()
    assert (WF / "sky-full-market-five-minute-dispatch.yml").is_file()
    assert (WF / "sky-full-market-private.yml").is_file()


def test_expired_ai_direction_watchdog_keeps_manual_diagnostics_only():
    content = (WF / "ai-direction-watchdog-5m.yml").read_text(encoding="utf-8")
    assert "  schedule:" not in content
    assert "*/5 * * * *" not in content
    assert "  workflow_dispatch:" in content
    assert "2026-11-09T02:38:00Z" in content
    assert "Sky Cloud Scanner" not in content
