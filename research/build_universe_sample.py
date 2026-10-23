
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import requests

TWSE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"

def _valid(code):
    return isinstance(code, str) and len(code) == 4 and code.isdigit() and code[0] != "0"

def _score(code, salt):
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()

def fetch_universe():
    out = []
    r = requests.get(TWSE_URL, timeout=30); r.raise_for_status()
    for x in r.json():
        code = str(x.get("Code") or x.get("證券代號") or "").strip()
        if _valid(code):
            out.append({"symbol": code, "exchange": "TWSE",
                        "name": x.get("Name") or x.get("證券名稱") or ""})
    r = requests.get(TPEX_URL, timeout=30); r.raise_for_status()
    for x in r.json():
        code = str(x.get("SecuritiesCompanyCode") or x.get("Code") or "").strip()
        if _valid(code):
            out.append({"symbol": code, "exchange": "TPEx",
                        "name": x.get("CompanyName") or x.get("Name") or ""})
    return out

def deterministic_sample(universe, twse_n, tpex_n, salt="sky-v05-expanded-v1"):
    by = {"TWSE": [], "TPEx": []}
    for x in universe:
        if x["exchange"] in by:
            by[x["exchange"]].append(x)
    sample = []
    for ex, n in [("TWSE", twse_n), ("TPEx", tpex_n)]:
        arr = sorted(by[ex], key=lambda x: _score(x["symbol"], salt))
        sample.extend(arr[:n])
    return sample

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--twse-n", type=int, default=50)
    ap.add_argument("--tpex-n", type=int, default=50)
    ap.add_argument("--out", default="research_data/universe_manifest.json")
    args = ap.parse_args()
    uni = fetch_universe()
    sample = deterministic_sample(uni, args.twse_n, args.tpex_n)
    p = Path(args.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "method":"deterministic SHA256 sample from current official TWSE/TPEx universe",
        "survivorship_bias_warning":"Uses current listing universe to look backward; delisted names are absent.",
        "twse_n":args.twse_n, "tpex_n":args.tpex_n, "sample":sample
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Universe={len(uni)} Sample={len(sample)} -> {p}")

if __name__ == "__main__":
    main()
