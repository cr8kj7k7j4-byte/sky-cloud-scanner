"""Read-only schema probe of official historical whole-market daily quotes.

Do not claim readiness based on this probe: only source schema/availability
is evaluated. No strategy or Production changes.
"""
import json
from src.http_utils import get_json


def run():
    endpoints={
        "TWSE_DATED_MI_INDEX":(
            "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX",
            {"date":"20261030","type":"ALLBUT0999","response":"json"},
        ),
        "TPEX_DATED_DAILY_CLOSE_QUOTES":(
            "https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php",
            {"l":"zh-tw","o":"json","d":"115/10/30"},
        ),
        "TPEX_DATED_NO1430":(
            "https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_wn1430_result.php",
            {"l":"zh-tw","d":"115/10/30","se":"EW"},
        ),
    }
    out={}
    for name,(url,params) in endpoints.items():
        try:
            obj=get_json(url,params=params,timeout=25,retries=2)
            out[name]={
                "status":"RESPONSE",
                "type":type(obj).__name__,
                "keys":list(obj.keys())[:25] if isinstance(obj,dict) else [],
                "stat":obj.get("stat") if isinstance(obj,dict) else None,
                "tables":[
                    {"fields":t.get("fields"),"rows":len(t.get("data") or []),"first":(t.get("data") or [])[:1]}
                    for t in obj.get("tables",[]) if isinstance(t,dict)
                ][:8] if isinstance(obj,dict) else [],
                "fields":obj.get("fields") if isinstance(obj,dict) else None,
                "data_count":len(obj.get("data") or []) if isinstance(obj,dict) else len(obj) if isinstance(obj,list) else None,
                "aaData_count":len(obj.get("aaData") or []) if isinstance(obj,dict) else None,
                "first_row":(obj.get("aaData") or obj.get("data") or [])[:1] if isinstance(obj,dict) else obj[:1] if isinstance(obj,list) else [],
            }
        except Exception as exc:
            out[name]={"status":"ERROR","error":f"{type(exc).__name__}:{str(exc)[:220]}"}
    print(json.dumps(out,ensure_ascii=False,indent=2))


if __name__=="__main__":
    run()
