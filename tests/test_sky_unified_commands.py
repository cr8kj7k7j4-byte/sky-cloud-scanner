from src.sky_command_router import route_command
from src.sky_unified_commands import REGISTRIES


def test_unified_market_route():
    route = route_command("Sky 全市場掃描")
    assert route.command_family == "SKY_UNIFIED_MARKET_SCAN"
    assert route.whole_market_required is True
    assert route.realtime_required is True
    assert "sky-unified-commands.yml" in route.execution_target


def test_unified_health_route():
    route = route_command("Sky 系統健康檢查")
    assert route.command_family == "SKY_UNIFIED_SYSTEM_HEALTH"
    assert route.realtime_required is False


def test_unified_validation_route():
    route = route_command("Sky 全模型驗證")
    assert route.command_family == "SKY_UNIFIED_MODEL_VALIDATION"
    assert route.data_mode == "GOVERNED_RESEARCH_EVIDENCE"


def test_required_registries_are_present():
    from pathlib import Path
    assert len(REGISTRIES) == 3
    assert all(Path(p).exists() for p in REGISTRIES)
