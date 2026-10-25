from __future__ import annotations
import argparse,json
from pathlib import Path
from src.official_universe_events import collect_official_events, write_snapshot
from src.point_in_time_universe import validate_intervals

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="research_output_pit/official_universe_snapshot.json")
    args=ap.parse_args()
    payload=collect_official_events()
    payload["interval_validation"]=validate_intervals(payload["intervals"])
    if not payload["interval_validation"]["valid"]:
        payload["production_eligible"]=False
    write_snapshot(args.out,payload)
    print(json.dumps({
        "health":payload["health"],
        "events":len(payload["events"]),
        "intervals":len(payload["intervals"]),
        "unresolved":len(payload["unresolved"]),
        "interval_validation":payload["interval_validation"],
        "production_eligible":payload["production_eligible"],
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
