from src.sky_command_router import route_command, presentation_for_command, watchlist_for_command


def test_sky_minimal_single_stock_command_requires_certified_quote():
    route = route_command("Sky 分析 2330")
    assert route.command_family == "SKY_SINGLE_STOCK_UPDATE"
    assert route.realtime_required is True
    assert route.symbol_required is True
    assert "HOLD/NO_TRADE" in route.notes


def test_sky_minimal_position_review_never_assumes_broker_holdings():
    route = route_command("Sky 持股檢查")
    assert route.command_family == "SKY_POSITION_REVIEW"
    assert "src.sky_manual_position_review.review_manual_positions" in route.execution_target
    assert route.realtime_required is False
    assert "no GitHub trigger" in route.execution_target
    assert "no broker connection" in route.notes.lower()


def test_whole_market_realtime_routes():
    for cmd in [
        "Sky 快掃",
        "Sky 當沖現在掃一次",
        "Sky Swing 5D 快掃",
        "Sky 波段現在掃一次",
        "Sky 波段快掃",
        "Sky Swing V1.1｜現在掃一次",
    ]:
        route = route_command(cmd)
        assert route.realtime_required is True
        assert route.whole_market_required is True


def test_single_stock_update_is_realtime():
    route = route_command("Sky 當沖更新 9914")
    assert route.data_mode == "SINGLE_STOCK_REALTIME"
    assert route.symbol_required is True


def test_position_update_is_realtime():
    route = route_command("Sky 波段持倉更新 2409，成本 37.05，1 張")
    assert route.realtime_required is True
    assert route.data_mode == "SINGLE_STOCK_REALTIME"


def test_backtest_stays_historical():
    route = route_command("Sky 回測目前模型")
    assert route.realtime_required is False
    assert route.data_mode == "HISTORICAL_PIT"


def test_unknown_current_sky_command_fails_closed():
    route = route_command("Sky 神秘快掃")
    assert route.data_mode == "REALTIME_REQUIRED_UNROUTED"
    assert route.execution_target == "ROUTER_REVIEW_REQUIRED"


def test_sky_swing_now_routes_to_governed_v10_observation_only():
    route = route_command("Sky 波段現在掃一次")
    assert route.command_family == "SKY_SWING_V10_LIVE_OBSERVATION"
    assert route.execution_target == ".github/workflows/swing-live-scan.yml --mode swing"
    assert route.data_mode == "WHOLE_MARKET_REALTIME_RESEARCH_ONLY"
    assert route.realtime_required is True
    assert route.whole_market_required is True
    assert "exact executable rule specification is BLOCKED" in route.notes
    assert "Swing V1.1 remains Research only" in route.notes


def test_swing_now_workflow_is_owner_only_on_w0_issue():
    from pathlib import Path
    workflow = Path(".github/workflows/swing-live-scan.yml").read_text(encoding="utf-8")
    assert "github.event.issue.number == 363" in workflow
    assert "github.event.comment.user.login == github.repository_owner" in workflow
    assert "github.event.comment.author_association == 'OWNER'" in workflow
    assert "github.event.comment.body == 'Sky 波段現在掃一次'" in workflow
    assert "github.event.comment.body == 'Sky Swing 5D 快掃'" in workflow
    assert "sky-fugle-paid-global-research-v1-live-wholemarket" in workflow
    assert "SKY_PAID_ATOMIC_ENFORCE: \"1\"" in workflow
    assert "- name: Run whole-market live swing scan\n        id: scan" in workflow
    assert "SCAN_OUTCOME: ${{ steps.scan.outcome }}" in workflow
    status_upload = workflow.split("- name: Upload connector-readable same-run status artifact", 1)[1]
    assert "if: always() && (github.event_name == 'push'" in status_upload.split("\n", 3)[1]


def test_sky_swing_quick_scan_remains_broad_candidate_scan():
    route = route_command("Sky 波段快掃")
    assert route.command_family == "SKY_SWING_SCAN"
    assert "src.swing_live_scanner --mode swing" in route.execution_target
    assert route.data_mode == "SESSION_ADAPTIVE_SWING_RESEARCH"
    assert "sky_swing_session_policy" in route.execution_target


def test_single_stock_update_requires_fugle_realtime_first():
    route = route_command("Sky 當沖更新 4960")
    assert route.realtime_required is True
    assert route.data_mode == "SINGLE_STOCK_REALTIME"
    assert "Fugle" in route.execution_target
    assert "MANDATORY" in route.notes
    assert "stale public web data must never substitute" in route.notes


def test_natural_language_daytrade_routes_to_realtime():
    route = route_command("1569 濱川 當沖要怎麼操作，請給我多空評分與停損")
    assert route.command_family == "SKY_SINGLE_STOCK_UPDATE"
    assert route.realtime_required is True
    assert route.data_mode == "SINGLE_STOCK_REALTIME"
    assert "Fugle" in route.execution_target


def test_full_market_research_visibility_routes_are_explicit():
    for cmd in ("Sky 全市場完整掃描", "Sky 六模型全市場即時掃描", "Sky 查詢六模型研究訊號"):
        route = route_command(cmd)
        assert route.command_family == "SKY_SIX_MODEL_RESEARCH_VISIBILITY"
        assert route.realtime_required is True
        assert route.whole_market_required is True
        assert "research_visibility" in route.execution_target


def test_single_stock_swing_update_is_realtime():
    route = route_command("Sky 波段更新 3717")
    assert route.command_family == "SKY_SINGLE_STOCK_UPDATE"
    assert route.data_mode == "SINGLE_STOCK_REALTIME"
    assert route.symbol_required is True
    assert route.realtime_required is True


def test_swing_quick_scan_alias_is_exact_owner_only_and_swing_mode():
    from pathlib import Path
    workflow = Path(".github/workflows/swing-live-scan.yml").read_text(encoding="utf-8")
    guard = workflow.split("jobs:", 1)[1].split("runs-on:", 1)[0]
    assert "github.event.issue.number == 363" in guard
    assert "github.event.comment.user.login == github.repository_owner" in guard
    assert "github.event.comment.author_association == 'OWNER'" in guard
    assert "github.event.comment.body == 'Sky 波段快掃'" in guard
    assert "github.event.comment.body == 'Sky Swing 5D 快掃'" in guard
    assert "github.event.comment.body == 'Sky 波段現在掃一次'" in guard
    assert "sky-fugle-paid-global-research-v1-live-wholemarket" in workflow
    # All four mode expressions (scanner, gate, readback, mobile summary) must agree.
    assert workflow.count("github.event.comment.body == 'Sky 波段快掃'") == 6
    assert workflow.count("&& 'swing')") == 4
    assert "id: scan" in workflow
    assert "SCAN_OUTCOME: ${{ steps.scan.outcome }}" in workflow
    assert "automatic_order" in workflow


def test_w0_shortcuts_are_classified_without_claiming_execution():
    cases = {
        "SKY維持率": ("SKY_MARGIN_MAINTENANCE_RESEARCH", False),
        "SKY當沖": ("SKY_DAYTRADE_SCAN", True),
        "SKY波段": ("SKY_SWING_V10_LIVE_OBSERVATION", True),
        "SKY盤中掃描": ("SKY_DAYTRADE_SCAN", True),
        "SKY盤後分析": ("SKY_POSTMARKET_RESEARCH", False),
        "SKY系統狀態": ("SKY_UNIFIED_SYSTEM_HEALTH", False),
        "SKY工程修復": ("SKY_W0_ENGINEERING_REVIEW", False),
        "SKY正式驗收": ("SKY_SEVEN_LAYER_ACCEPTANCE", False),
    }
    for name, (family, realtime) in cases.items():
        route = route_command(name)
        assert route.command_family == family
        assert route.realtime_required is realtime
        assert route.command_family != "SKY_UNRECOGNIZED"


def test_margin_ratio_is_never_marked_trade_ready_without_verified_source():
    route = route_command("Sky 維持率")
    assert route.data_mode == "RESEARCH_ONLY_SOURCE_UNVERIFIED"
    assert route.execution_target == "HOLD_PROVIDER_AND_SOURCE_CONFIRMATION"
    assert "No live" in route.notes
    assert route.whole_market_required is False


def test_margin_watchlist_and_project_mobile_presentation_contract():
    symbols = watchlist_for_command("SKY維持率")
    assert symbols == (
        "2337", "6217", "3362", "8045", "8043", "2233",
        "5464", "4764", "1587", "3447", "2230", "6994",
    )
    assert len(symbols) == len(set(symbols)) == 12
    removed_over_100 = {
        "4979", "8039", "8358", "3026", "3363",
        "3532", "3211", "8021", "6683",
    }
    assert not removed_over_100.intersection(symbols)
    assert watchlist_for_command("SKY當沖") is None
    assert presentation_for_command("SKY維持率") == "SKY_MOBILE_TABLE_V1_0"
    route = route_command("SKY維持率")
    assert route.data_mode == "RESEARCH_ONLY_SOURCE_UNVERIFIED"
    assert route.whole_market_required is False
    assert route.execution_target == "HOLD_PROVIDER_AND_SOURCE_CONFIRMATION"


def test_unregistered_current_command_still_fails_closed():
    route = route_command("SKY未知更新")
    assert route.command_family == "SKY_UNRECOGNIZED"
    assert route.execution_target == "ROUTER_REVIEW_REQUIRED"



def test_unrelated_issue_comments_cannot_evict_pending_paid_scans():
    from pathlib import Path

    swing = Path(".github/workflows/swing-live-scan.yml").read_text(encoding="utf-8")
    v11 = Path(".github/workflows/swing-v11-live-scan.yml").read_text(encoding="utf-8")
    bridge = Path(".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
    assert "sky-swing-ignored-{0}" in swing
    assert "sky-swing-v11-ignored-{0}" in v11
    assert "sky-chat-ignored-{0}" in bridge
    for workflow in (swing, v11, bridge):
        concurrency = workflow.split("concurrency:", 1)[1].split("jobs:", 1)[0]
        assert "github.run_id" in concurrency
        assert "sky-fugle-paid-global-research-v1-live-wholemarket" in concurrency
        assert "cancel-in-progress: false" in concurrency
        assert "github.event.comment.author_association == 'OWNER'" in concurrency


def test_five_minimal_mobile_commands_share_presentation_only():
    from src.sky_command_router import presentation_for_command
    for command in ("Sky 當沖快掃", "Sky 波段快掃", "SKY維持率", "Sky 分析 2330", "Sky 持股檢查"):
        assert presentation_for_command(command) == "SKY_MOBILE_TABLE_V1_0"
    assert presentation_for_command("Sky 分析 not-a-symbol") is None
    assert "src.sky_manual_position_review.review_manual_positions" in route_command("Sky 持股檢查").execution_target
    assert route_command("SKY維持率").execution_target == "HOLD_PROVIDER_AND_SOURCE_CONFIRMATION"

def test_session_and_historical_research_contracts_in_existing_acceptance_ci():
    """Run off-hours selectors plus historical readback without any new Workflow."""
    import unittest
    from tests import (
        test_sky_daytrade_session_policy,
        test_sky_swing_session_policy,
        test_sky_historical_research_readback,
    )

    loader = unittest.TestLoader()
    suite = unittest.TestSuite(
        loader.loadTestsFromModule(module)
        for module in (
            test_sky_daytrade_session_policy,
            test_sky_swing_session_policy,
            test_sky_historical_research_readback,
        )
    )
    count = suite.countTestCases()
    assert count >= 20, f"Unexpectedly incomplete session/readback suite: {count}"
    result = unittest.TestResult()
    suite.run(result)
    assert result.wasSuccessful(), (
        "Off-hours session/historical contract failures: "
        + repr(result.failures + result.errors)
    )
    assert result.testsRun == count
