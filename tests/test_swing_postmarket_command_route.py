"""Regression test for Sky swing postmarket review command routing."""
from src.sky_command_router import route_command


def test_swing_postmarket_review_route():
    for command in ("Sky 盤後複盤｜波段", "Sky 盤後複盤|波段", "Sky 盤後複盤 波段"):
        result = route_command(command)
        assert result.command_family == "SKY_SWING_POSTMARKET_REVIEW"
        assert result.data_mode == "POSTMARKET_DAILY_AND_SIGNAL_LEDGER"
        assert result.realtime_required is False
        assert result.whole_market_required is True
        assert "swing-postmarket-research.yml" in result.execution_target
        assert "UNKNOWN" in result.notes
