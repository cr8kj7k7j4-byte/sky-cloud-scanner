import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.observability import ServiceMetric,health_snapshot
from src.slo_engine import evaluate_platform


def main():
    healthy=[
        ServiceMetric("TWSE",True,500,20,0.0,0.999),
        ServiceMetric("TPEX",True,600,30,0.0,0.999),
        ServiceMetric("FUGLE",True,300,5,0.0,0.995),
        ServiceMetric("RISK_ENGINE",True,50,1,0.0,1.0),
        ServiceMetric("ALERT_ENGINE",True,200,10,0.0,0.995),
        ServiceMetric("STATE_STORE",True,80,2,0.0,1.0),
    ]
    snap=health_snapshot(healthy)
    assert snap["all_available"] is True

    report=evaluate_platform(healthy)
    assert report["mode"]=="NORMAL"
    assert report["new_entries_allowed"] is True
    assert report["live_activation_allowed"] is False

    broken=list(healthy)
    broken[0]=ServiceMetric("TWSE",False,8000,999,1.0,0.0)
    bad=evaluate_platform(broken)
    assert bad["mode"]=="LOCKDOWN"
    assert "TWSE" in bad["critical_failed_services"]
    assert bad["new_entries_allowed"] is False

    soft=list(healthy)
    soft[2]=ServiceMetric("FUGLE",True,5000,60,0.02,0.98)
    degraded=evaluate_platform(soft)
    assert degraded["mode"]=="OBSERVE_ONLY"
    assert "FUGLE" in degraded["failed_services"]

    print("PASS Observability + SLO Health Dashboard tests")


if __name__=="__main__":
    main()
