"""W0 #363: fail-closed V1.1 on-demand workflow wiring (no paid API calls)."""
from pathlib import Path

WORKFLOW = Path(".github/workflows/swing-v11-live-scan.yml")


def test_exact_owner_comment_and_no_schedule():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "issue_comment:" in source
    assert "github.event.issue.number == 363" in source
    assert "github.event.comment.user.login == github.repository_owner" in source
    assert "github.event.comment.author_association == 'OWNER'" in source
    assert "github.event.comment.body == 'Sky Swing V1.1｜現在掃一次'" in source
    assert "github.event_name == 'workflow_dispatch'" in source
    assert "\n  schedule:" not in source
    assert "production_eligible\":False" in source
    assert "automatic_order\":False" in source


def test_stale_daily_blocks_before_paid_fugle():
    source = WORKFLOW.read_text(encoding="utf-8")
    daily = source.index("- name: Reject stale or unverifiable canonical daily signal")
    guard = source.index("- name: Reserve shared Fugle paid API slot")
    claim = source.index("- name: Publish reservation before paid API call")
    verify = source.index("- name: Verify reservation claim independently")
    paid = source.index("- name: Run V1.1 whole-market live scan")
    secondary = source.index("- name: Collect current TWSE TPEx daily market")
    assert daily < guard < claim < verify < paid < secondary
    assert "BLOCKED_STALE_OR_UNVERIFIED_CANONICAL_DAILY_NO_PAID_API" in source
    assert "--scope 'sky:live:wholemarket'" in source
    assert "group: sky-fugle-paid-global-research-v1-live-wholemarket" in source
    assert "if: steps.verify_claim.outcome == 'success'" in source
    assert "if: steps.guard.outputs.allowed == 'true'" in source
    assert "cancel-in-progress: false" in source


def test_preflight_fails_closed_and_preserves_research():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "choose_signal_date(load_daily_history(" in source
    assert "load_signal_date_guard(" in source
    assert 'status.get("status") != "PASS"' in source
    assert "output/swing_v11_live/preflight_gate.json" in source
    assert "output/swing_v11_live/" in source
    assert "run_id: 40252311345" not in source
    assert "BLOCKED_UNVERIFIED_CANONICAL_SOURCE_IDENTITY" in source
    assert "SOURCE_IDENTITY_CONFIGURED_NOT_FRESHNESS_CERTIFIED" in source
    assert "SKY_SWING_CANONICAL_DAILY_RUN_ID" in source
    assert "SKY_SWING_CANONICAL_DAILY_ARTIFACT_NAME" in source
    assert "source_run_id:" in source and "artifact_name:" in source
    assert "if: steps.daily_source.outcome == 'success'" in source
    assert "run_id: ${{ steps.daily_source.outputs.run_id }}" in source
    assert "name: ${{ steps.daily_source.outputs.artifact_name }}" in source
