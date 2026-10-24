from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.observability import ServiceMetric, health_snapshot
from src.slo_engine import evaluate_platform


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True,help="JSON list of service metrics")
    ap.add_argument("--out",default="research_output/health_dashboard.json")
    args=ap.parse_args()

    raw=json.loads(Path(args.input).read_text(encoding="utf-8"))
    metrics=[ServiceMetric(**x) for x in raw]
    report={
        "snapshot":health_snapshot(metrics),
        "slo":evaluate_platform(metrics),
        "dashboard_sections":[
            "TWSE","TPEX","FUGLE","RISK_ENGINE","ALERT_ENGINE","STATE_STORE"
        ],
        "live_order_allowed":False,
    }

    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
