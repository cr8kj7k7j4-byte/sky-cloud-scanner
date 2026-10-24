import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.champion_challenger import ShadowOutcome, compare_roles, compare_by_regime
from src.challenger_promotion_review import challenger_review


def main():
    rows=[
        ShadowOutcome("e1","CHAMPION","2.1","2409","BULL",True,True,True,0.4,1.0,0.4,False,False,None),
        ShadowOutcome("e2","CHAMPION","2.1","3481","BULL",True,True,True,-0.2,0.5,0.9,True,False,None),
        ShadowOutcome("e3","CHAMPION","2.1","6770","NEUTRAL",False,False,False,None,None,None,False,True,"NO_SIGNAL"),
        ShadowOutcome("e1","CHALLENGER","2.2","2409","BULL",True,True,True,0.7,1.3,0.3,False,False,None),
        ShadowOutcome("e2","CHALLENGER","2.2","3481","BULL",True,True,True,0.1,0.8,0.5,False,False,None),
        ShadowOutcome("e3","CHALLENGER","2.2","6770","NEUTRAL",True,True,True,0.2,0.6,0.4,False,False,None),
    ]
    comp=compare_roles(rows)
    assert comp["challenger"]["expectancy_r"] > comp["champion"]["expectancy_r"]
    assert comp["delta"]["false_breakouts"] > 0
    assert comp["delta"]["missed_opportunities"] > 0

    regimes=compare_by_regime(rows)
    assert "BULL" in regimes
    assert "NEUTRAL" in regimes

    review=challenger_review(
        comp,
        min_events=3,
        regime_comparisons=regimes,
        require_regime_consistency=False,
    )
    assert review["governance_review_ready"] is True
    assert review["automatic_promotion_allowed"] is False

    print("PASS Champion vs Challenger Shadow Evaluation tests")


if __name__=="__main__":
    main()
