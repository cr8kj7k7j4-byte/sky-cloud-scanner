from src.swing_live_scanner import MODE_META, coverage_governance_notice


def test_incomplete_market_does_not_claim_realtime_coverage():
    notice = coverage_governance_notice(False, 4.53)
    assert "未通過驗證" in notice
    assert "4.53%" in notice
    assert "不可據此產生 A+" in notice
    assert "TPEx 官方完整即時行情" in notice
    assert "全市場即時資料可用" not in MODE_META["swing"]["note"]


def test_certified_operational_market_still_disclaims_otc_official_status():
    notice = coverage_governance_notice(True, 81.0)
    assert "覆蓋驗證通過" in notice
    assert "OTC MIS" in notice
    assert "非 TPEx 官方完整即時行情" in notice
