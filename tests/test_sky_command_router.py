from src.sky_command_router import route_command


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
    assert route.execution_target == "src.swing_live_scanner --mode swing"


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
    assert workflow.count("github.event.comment.body == 'Sky 波段快掃'") == 5
    assert workflow.count("&& 'swing')") == 4
    assert "id: scan" in workflow
    assert "SCAN_OUTCOME: ${{ steps.scan.outcome }}" in workflow
    assert "automatic_order" in workflow
