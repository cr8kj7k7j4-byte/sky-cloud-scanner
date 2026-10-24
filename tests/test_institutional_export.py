import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from research.export_institutional_history import parse_twse_json,parse_tpex_new,parse_tpex_old,roc_date,n

def main():
    assert n("1,234")==1234 and n("(100)")==-100 and n("－25")==-25
    assert roc_date("2026-10-22")=="115/10/22"

    tw={"stat":"OK",
        "fields":["證券代號","證券名稱","外陸資買賣超股數(不含外資自營商)","外資自營商買賣超股數","投信買賣超股數","自營商買賣超股數","三大法人買賣超股數"],
        "data":[["2330","台積電","1000","20","30","-50","1000"]]}
    r=parse_twse_json(tw,"2026-10-22")
    assert len(r)==1 and r[0]["foreign_net"]==1020 and r[0]["total_inst_net"]==1000

    row=["6488","環球晶"]+["0"]*22
    row[10]="100"; row[13]="20"; row[22]="-10"; row[23]="110"
    assert parse_tpex_new({"tables":[{"data":[row]}]},"2026-10-22")[0]["dealer_net"]==-10
    assert parse_tpex_old({"aaData":[row]},"2026-10-22")[0]["total_inst_net"]==110

    bad=row.copy(); bad[23]="999"
    assert parse_tpex_new({"tables":[{"data":[bad]}]},"2026-10-22")==[]
    print("PASS 6/6 institutional-export unit tests")

if __name__=="__main__": main()
