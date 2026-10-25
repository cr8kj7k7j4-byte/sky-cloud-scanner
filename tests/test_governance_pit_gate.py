import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_registry_marks_p0s_rejected_oos():
    text = (ROOT / "SKY_SYSTEM_REGISTRY_V2_1.md").read_text(encoding="utf-8")
    assert "P0-S 5m Breakout Candidate | REJECTED_OOS" in text
    assert "OOS n=9,111" in text
    assert "PF=0.2033" in text
    assert "Expectancy=-0.8018R" in text


def test_revenue_candidates_are_pre_pit_only():
    text = (ROOT / "SKY_SYSTEM_REGISTRY_V2_1.md").read_text(encoding="utf-8")
    assert "Revenue MoM 5D | PRE_PIT_CANDIDATE" in text
    assert "Revenue YoY Acceleration 5D | PRE_PIT_CANDIDATE" in text


def test_revenue_research_hard_blocks_promotion_before_pit():
    text = (ROOT / "research" / "research_monthly_revenue_oos.py").read_text(encoding="utf-8")
    assert '"point_in_time_verified":False' in text
    assert '"promotion_candidates":[]' in text
    assert 'report["pre_pit_candidates"].append(key)' in text
    assert 'report["promotion_candidates"].append(key)' not in text


def test_live_scanner_disables_rejected_breakout_by_default():
    cfg = (ROOT / "src" / "config.py").read_text(encoding="utf-8")
    main = (ROOT / "src" / "main.py").read_text(encoding="utf-8")
    assert 'P0S_5M_BREAKOUT_ENABLED = _b("P0S_5M_BREAKOUT_ENABLED", "0")' in cfg
    assert "if P0S_5M_BREAKOUT_ENABLED" in main
    assert '"verdict": P0S_OOS_VERDICT' in main
