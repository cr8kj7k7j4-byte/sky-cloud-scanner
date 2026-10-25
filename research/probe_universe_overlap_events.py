from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from src.official_universe_events import collect_official_events

TARGETS={"5364","6472","2465","2482","2486","2491","6133","6873"}

def main():
    payload=collect_official_events()
    events=[
        x for x in payload.get("events",[])
        if str(x.get("symbol")) in TARGETS
    ]
    events=sorted(events,key=lambda x:(x["symbol"],x["exchange"],x["event_date"],x["event_type"]))
    unresolved=payload.get("unresolved") or []
    counts=Counter((x.get("exchange"),x.get("reason")) for x in unresolved)
    report={
        "target_events":events,
        "unresolved_total":len(unresolved),
        "unresolved_counts":{
            f"{k[0]}|{k[1]}":v for k,v in sorted(counts.items())
        },
        "unresolved_sample":unresolved[:200],
    }
    out=Path("output/universe_overlap_probe")
    out.mkdir(parents=True,exist_ok=True)
    (out/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
