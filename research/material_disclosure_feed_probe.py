"""Current official TWSE/TPEx material-disclosure feed schema reconnaissance.
Not a historic issuer filing-time source; no saved confidential content.
"""
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request,urlopen

SOURCES={
 "TWSE_CURRENT_MATERIAL_DISCLOSURES":"https://openapi.twse.com.tw/v1/opendata/t187ap04_L",
 "TPEX_CURRENT_MATERIAL_DISCLOSURES":"https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O",
}
def probe(url):
 try:
  with urlopen(Request(url,headers={"User-Agent":"SkyDisclosureSourceAudit/1.0"}),timeout=20) as r:
   payload=json.loads(r.read(12_000_000).decode("utf-8-sig"))
   status=r.status
  if not isinstance(payload,list):
   return {"http_status":status,"json_array":False,"historical_filing_time_verified":False}
  names=sorted({k for row in payload[:10] if isinstance(row,dict) for k in row.keys()})
  return {"http_status":status,"json_array":True,"row_count":len(payload),
   "sample_field_names":names,
   "historical_filing_time_verified":False,
   "current_feed_issuer_time_verified":False,
   "reason":"A current announcement feed may expose a time field; cannot infer archived monthly revenue or historical earnings PIT without record-level verification."}
 except Exception as e:
  return {"error":type(e).__name__+": "+str(e)[:160],
   "historical_filing_time_verified":False,
   "current_feed_issuer_time_verified":False}

if __name__=="__main__":
 ap=argparse.ArgumentParser()
 ap.add_argument("--out",default="research_output/material_disclosure_feed_probe.json")
 a=ap.parse_args()
 report={"checked_at_utc":datetime.now(timezone.utc).isoformat(),
  "status":"INSUFFICIENT_DATA","production_signal":False,
  "sources":{name:probe(url) for name,url in SOURCES.items()},
  "caveat":"Material disclosures and monthly revenue actual published_at are not equivalent"}
 dest=Path(a.out);dest.parent.mkdir(exist_ok=True,parents=True)
 dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(report,ensure_ascii=False))
