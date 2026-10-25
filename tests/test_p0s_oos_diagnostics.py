import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.backtest_p0s_breakout_oos import (
    diagnostic_breakdown,
    cost_sensitivity,
    excursion_structure,
)

def main():
    rows=[
        {"exit_reason":"STOP","trigger_time":"09:20","risk_pct":0.5,"gross_r":-1.0,"net_r":-1.9,"mfe_r":0.2,"mae_r":-1.0},
        {"exit_reason":"TARGET","trigger_time":"09:40","risk_pct":1.0,"gross_r":2.0,"net_r":1.55,"mfe_r":2.2,"mae_r":-0.2},
        {"exit_reason":"TIME","trigger_time":"10:15","risk_pct":1.4,"gross_r":0.3,"net_r":-0.02,"mfe_r":0.8,"mae_r":-0.4},
    ]
    d=diagnostic_breakdown(rows)
    assert "exit:STOP" in d
    assert "time:09:00-09:29" in d
    assert "risk:0.30-0.60" in d
    c=cost_sensitivity(rows)
    assert "0.00%" in c and "0.45%" in c
    e=excursion_structure(rows)
    assert e["share_mfe_ge_2r"] > 0
    print("PASS P0-S OOS diagnostic tests")

if __name__=="__main__":
    main()
