from datetime import datetime
from zoneinfo import ZoneInfo
import json
from .official import load_official_universe,fetch_mis_quotes
from .fugle import snapshot_quotes

def run():
    out={"time":datetime.now(ZoneInfo("Asia/Taipei")).isoformat()}
    u,st=load_official_universe(); out["official_universe"]=st; out["universe_count"]=len(u)
    q,w=fetch_mis_quotes(u[:120]); out["mis_sample"]={"requested":min(120,len(u)),"returned":len(q),"warnings":w}
    for m in ("TSE","OTC"):
        try:
            p=snapshot_quotes(m); out[f"fugle_snapshot_{m}"]={"ok":True,"date":p.get("date"),"time":p.get("time"),"count":len(p.get("data",[]))}
        except Exception as e: out[f"fugle_snapshot_{m}"]={"ok":False,"error":f"{type(e).__name__}: {e}"}
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__": run()
