
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.export_official_enrichment import (
    normalize_twse_row, normalize_tpex_row, roc_to_iso,
    parse_taiex_payload, month_starts, build_industry
)

def main():
    tw=normalize_twse_row({"公司代號":"2330","公司簡稱":"台積電","產業別":"24"})
    assert tw["symbol"]=="2330" and tw["industry_code"]=="24" and tw["market"]=="TWSE"

    tp=normalize_tpex_row({
        "SecuritiesCompanyCode":"6488",
        "CompanyAbbreviation":"環球晶",
        "SecuritiesIndustryCode":"24"
    })
    assert tp["symbol"]=="6488" and tp["industry_code"]=="24" and tp["market"]=="TPEx"

    assert roc_to_iso("112/05/23")=="2023-05-23"
    assert month_starts("2023-05-23","2023-07-01")==["20230501","20230601","20230701"]

    payload={
        "fields":["日期","開盤指數","最高指數","最低指數","收盤指數"],
        "data":[["112/05/23","16,200.00","16,250.00","16,100.00","16,220.00"]]
    }
    p=parse_taiex_payload(payload)
    assert p[0]["date"]=="2023-05-23" and p[0]["close"]==16220.0

    manifest={"sample":[
        {"symbol":"2330","exchange":"TWSE","name":"台積電"},
        {"symbol":"6488","exchange":"TPEx","name":"環球晶"},
    ]}
    rows,missing=build_industry(
        manifest,
        [{"公司代號":"2330","公司簡稱":"台積電","產業別":"24"}],
        [{"SecuritiesCompanyCode":"6488","CompanyAbbreviation":"環球晶","SecuritiesIndustryCode":"24"}]
    )
    assert len(rows)==2 and not missing
    assert {x["market"] for x in rows}=={"TWSE","TPEx"}

    print("PASS 7/7 official-enrichment unit tests")

if __name__=="__main__":
    main()
