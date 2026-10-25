from src.corporate_actions import CorporateAction, validate_actions, resolve_symbol, continuity_chain

def test_symbol_change_continuity():
    a=CorporateAction(symbol="1234",action_type="SYMBOL_CHANGE",effective_date="2026-01-05",source="TWSE",source_as_of="2026-01-05T00:00:00+08:00",old_symbol="1234",new_symbol="5678")
    assert validate_actions([a])["valid"] is True
    assert resolve_symbol("1234","2025-12-31",[a])=="1234"
    assert resolve_symbol("1234","2026-01-05",[a])=="5678"
    assert continuity_chain("1234",[a])==["1234","5678"]
