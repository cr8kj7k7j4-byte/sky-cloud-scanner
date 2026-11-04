"""Safety regression for eliminating duplicate GitHub Actions notifications and triggers."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"


def test_broad_telegram_workflow_no_longer_fans_out_on_every_action_or_push():
    text = (WF / "telegram-all-github-events.yml").read_text(encoding="utf-8")
    event_block = text.split("\npermissions:", 1)[0]
    assert "\n  workflow_run:" not in event_block
    assert "\n  push:" not in event_block
    assert "\n  issues:" in event_block
    assert "\n  pull_request:" in event_block
    assert "\n  issue_comment:" in event_block


def test_deleting_consumed_scan_request_does_not_run_scanner():
    text = (WF / "swing-live-scan.yml").read_text(encoding="utf-8")
    job = text.split("\njobs:", 1)[1].split("\n    runs-on:", 1)[0]
    assert "github.event_name != 'push'" in job
    assert "github.event.commits.*.added" in job
    assert "github.event.commits.*.modified" in job
    assert "github.event.commits.*.removed" not in job


def test_intraday_and_monitoring_failure_notifications_remain():
    intraday = (WF / "scan.yml").read_text(encoding="utf-8")
    monitor = (WF / "p0ops-continuous-monitor.yml").read_text(encoding="utf-8")
    assert "Notify Telegram when intraday scan fails" in intraday
    assert "Notify Telegram on monitoring errors" in monitor
