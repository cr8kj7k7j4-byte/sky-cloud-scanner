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


def test_sky_swing_now_aliases_v11_intraday_overlay():
    route = route_command("Sky 波段現在掃一次")
    assert route.command_family == "SKY_SWING_V11_LIVE_ALIAS"
    assert route.execution_target == "src.swing_v11_live_scanner"
    assert route.data_mode == "WHOLE_MARKET_REALTIME_PLUS_CANONICAL_DAILY"


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
