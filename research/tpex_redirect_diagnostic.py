"""TPEx redirect diagnostics; limited public GET requests only, no bypass."""
import json
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone

HOST="https://www.tpex.org.tw"
PATHS=["/openapi/v1/mopsfin_t187ap05_O","/openapi/v1/mopsfin_t187ap04_O",
       "/openapi/swagger.json"]
class BlockRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None

def probe(path):
    req=Request(HOST+path,headers={"User-Agent":"SkySourceDiagnostics/1.0","Accept":"application/json"})
    try:
        with build_opener(BlockRedirect()).open(req,timeout=15) as resp:
            return {"status":resp.status,"type":resp.headers.get("Content-Type"),"bytes_preview":len(resp.read(128)),"redirect_host":None}
    except HTTPError as e:
        location=e.headers.get("Location","")
        p=urlparse(location)
        return {"status":e.code,"redirect_host":p.hostname,"redirect_path":p.path,
                "redirect_query_present":bool(p.query),"server":e.headers.get("Server"),
                "retry_after":e.headers.get("Retry-After")}
    except (URLError,TimeoutError,OSError) as e:
        return {"error_type":type(e).__name__}
if __name__=="__main__":
    print(json.dumps({"at_utc":datetime.now(timezone.utc).isoformat(),
      "tests":{x:probe(x) for x in PATHS},"no_bypass":True},ensure_ascii=False))
