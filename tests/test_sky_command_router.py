from src.sky_command_router import route_command, presentation_for_command, watchlist_for_command


def test_sky_minimal_single_stock_command_requires_certified_quote():
    route = route_command("Sky 分析 2330")
    assert route.command_family == "SKY_SINGLE_STOCK_UPDATE"
    assert route.realtime_required is True
    assert route.symbol_required is True
    assert "HOLD/NO_TRADE" in route.notes
    assert route.data_mode == "SESSION_ADAPTIVE_SINGLE_STOCK_RESEARCH"
    assert "sky_daytrade_session_policy" in route.execution_target
    assert "verified complete-session historical" in route.execution_target


def test_single_stock_3717_off_hours_requires_historical_source_and_no_dispatch():
    route = route_command("Sky 分析 3717")
    assert route.command_family == "SKY_SINGLE_STOCK_UPDATE"
    assert route.symbol_required and not route.whole_market_required
    assert route.data_mode == "SESSION_ADAPTIVE_SINGLE_STOCK_RESEARCH"
    assert "same-run SHA/Artifact/Digest" in route.notes
    assert "no automatic dispatch" in route.execution_target
    assert "Private broker holdings" in route.notes
    assert "HOLD/NO_TRADE" in route.notes
    assert presentation_for_command("Sky 分析 3717") == "SKY_MOBILE_TABLE_V1_0"


def test_live_single_stock_updates_remain_realtime_and_independent():
    route = route_command("Sky 波段更新 3717")
    assert route.data_mode == "SINGLE_STOCK_REALTIME"
    assert route.realtime_required
    assert "Fugle" in route.execution_target


def test_unverified_single_stock_cannot_fall_back_to_public_history():
    route = route_command("Sky 分析 3717")
    assert "No stale quote becomes current" in route.notes
    assert "Missing evidence stays HOLD/NO_TRADE" in route.notes


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


def test_sky_swing_now_routes_to_frozen_v11_research_only():
    route = route_command("Sky 波段現在掃一次")
    assert route.command_family == "SKY_SWING_V11_LIVE"
    assert route.execution_target.startswith(".github/workflows/swing-v11-live-scan.yml")
    assert route.data_mode == "WHOLE_MARKET_REALTIME_PLUS_CANONICAL_DAILY"
    assert route.realtime_required and route.whole_market_required
    assert "V1.0 remains Production" in route.notes
    assert "no buy approval" in route.notes


def test_swing_now_workflow_is_owner_only_and_never_double_triggers():
    from pathlib import Path
    old = Path(".github/workflows/swing-live-scan.yml").read_text(encoding="utf-8")
    v11 = Path(".github/workflows/swing-v11-live-scan.yml").read_text(encoding="utf-8")
    for text in ("Sky 波段快掃", "Sky 波段現在掃一次"):
        exact = "github.event.comment.body == '" + text + "'"
        assert exact not in old
        assert v11.count(exact) == 2  # concurrency and real live-scan job
    for owner in ("github.event.issue.number == 363",
                  "github.event.comment.user.login == github.repository_owner",
                  "github.event.comment.author_association == 'OWNER'"):
        assert owner in v11
    assert "github.event.comment.body == 'Sky Swing 5D 快掃'" in old
    assert "sky-fugle-paid-global-research-v1-live-wholemarket" in old
    assert "sky-fugle-paid-global-research-v1-live-wholemarket" in v11
    assert "SKY_PAID_ATOMIC_ENFORCE" in v11
    assert "steps.verify_claim.outcome == 'success'" in v11
    assert "github.event_name == 'workflow_dispatch'" in old


def test_sky_swing_quick_scan_uses_existing_frozen_research_runner():
    route = route_command("Sky 波段快掃")
    direct = route_command("Sky Swing V1.1｜現在掃一次")
    assert route.command_family == direct.command_family == "SKY_SWING_V11_LIVE"
    assert "swing-v11-live-scan.yml" in route.execution_target
    assert route.data_mode == direct.data_mode
    assert "No orders" in route.notes or "No orders" in route.notes.capitalize()


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


def test_swing_quick_scan_alias_is_unique_v11_owner_research():
    from pathlib import Path
    old = Path(".github/workflows/swing-live-scan.yml").read_text(encoding="utf-8")
    v11 = Path(".github/workflows/swing-v11-live-scan.yml").read_text(encoding="utf-8")
    for alias in ("Sky 波段快掃", "Sky 波段現在掃一次"):
        exact = "github.event.comment.body == '" + alias + "'"
        assert exact not in old
        assert v11.count(exact) == 2
    assert "github.event.comment.body == 'Sky Swing 5D 快掃'" in old
    assert "src.swing_v11_live_scanner" in v11
    assert "BLOCKED_UNVERIFIED_CANONICAL_SOURCE_IDENTITY" in v11
    assert "BLOCKED_STALE_OR_UNVERIFIED_CANONICAL_DAILY_NO_PAID_API" in v11
    assert "automatic_order" in v11 and "trade_action" in v11


def test_v11_same_run_readback_is_parseable_and_fail_closed():
    import ast
    from pathlib import Path
    from textwrap import dedent

    flow = Path(".github/workflows/swing-v11-live-scan.yml").read_text(encoding="utf-8")
    block = flow.split("- name: Independently read back same-run V1.1 research Artifact", 1)[1].split(
        "- name: Upload independent same-run V1.1 receipt", 1
    )[0]
    assert "gh run download" in block
    assert "--name \"sky-swing-v11-live-$GITHUB_RUN_ID\"" in block
    assert "V11_SHA256_MISMATCH" in block
    assert "V11_ARTIFACT_INVENTORY_MISMATCH" in block
    assert "PASS_HOLD_RECEIPT_INTEGRITY_ONLY" in block
    assert "production_eligible\":False" in block
    assert "automatic_order\":False" in block
    python = block.split("          python - <<'PY'\\n", 1)[1].split("\\n          PY", 1)[0]
    ast.parse(dedent(python))


def test_w0_shortcuts_are_classified_without_claiming_execution():
    cases = {
        "SKY維持率": ("SKY_PRICE_ONLY_RESEARCH", False),
        "SKY當沖": ("SKY_DAYTRADE_SCAN", True),
        "SKY波段": ("SKY_SWING_V11_LIVE", True),
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


def test_margin_ratio_estimate_does_not_bypass_trade_gates():
    route = route_command("Sky 維持率")
    assert route.data_mode == "PRICE_ONLY_OBSERVATION"
    assert route.execution_target == "src.sky_margin_runtime.evaluate_margin_bundle (offline; live source HOLD)"
    assert "NOT a low-margin-maintenance" in route.notes
    assert "RETIRED" in route.notes
    assert "P0-R" in route.notes
    assert "HOLD/NO_TRADE" in route.notes
    assert route.whole_market_required is True


def test_margin_watchlist_and_project_mobile_presentation_contract():
    symbols = watchlist_for_command("SKY維持率")
    assert symbols == (
        "2337", "6217", "3362", "8045", "8043", "2233",
        "5464", "4764", "1587", "3447", "2230", "6994",
        "3040", "6558", "3207", "3322",
    )
    assert len(symbols) == len(set(symbols)) == 16
    removed_over_100 = {
        "4979", "8039", "8358", "3026", "3363",
        "3532", "3211", "8021", "6683",
    }
    assert not removed_over_100.intersection(symbols)
    assert watchlist_for_command("SKY當沖") is None
    assert presentation_for_command("SKY維持率") == "SKY_MOBILE_TABLE_V1_0"
    route = route_command("SKY維持率")
    assert route.data_mode == "PRICE_ONLY_OBSERVATION"
    assert route.whole_market_required is True
    assert route.execution_target == "src.sky_margin_runtime.evaluate_margin_bundle (offline; live source HOLD)"


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
    assert route_command("SKY維持率").execution_target == "src.sky_margin_runtime.evaluate_margin_bundle (offline; live source HOLD)"

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



def test_shared_postmarket_inventory_in_existing_acceptance_ci():
    """PR CI must exercise exact source inventory writer used by both scan jobs."""
    import unittest
    from tests import test_sky_source_inventory

    suite = unittest.TestLoader().loadTestsFromModule(test_sky_source_inventory)
    assert suite.countTestCases() == 5
    result = unittest.TestResult()
    suite.run(result)
    assert result.wasSuccessful(), repr(result.failures + result.errors)
    assert result.testsRun == 5
