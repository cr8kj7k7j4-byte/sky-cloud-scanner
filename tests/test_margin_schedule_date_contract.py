"""Regression: midnight-delayed GitHub cron must not shift official margin day."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scheduled_margin_collector_uses_utc_schedule_day():
    workflow = (ROOT / ".github/workflows/margin-evidence.yml").read_text()
    assert 'cron: "30 15 * * 1-5"' in workflow
    assert 'REPORT_DATE="$(date -u +%F)"' in workflow
    assert 'DATE_BASIS="SCHEDULED_UTC_DATE_TAIPEI_2330"' in workflow
    assert 'src.trading_calendar --date "${{ steps.report_date.outputs.report_date }}"' in workflow
    assert 'collect.py --date "${{ steps.report_date.outputs.report_date }}"' in workflow


def test_manual_margin_historical_report_date_input_is_validated():
    workflow = (ROOT / ".github/workflows/margin-evidence.yml").read_text()
    assert "report_date:" in workflow
    assert 'REPORT_DATE="${{ inputs.report_date }}"' in workflow
    assert '[[ "$REPORT_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]' in workflow
