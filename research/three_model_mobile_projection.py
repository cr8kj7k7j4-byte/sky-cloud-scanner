"""Research-only mobile data contract: no live prices, no trade authorization, no Cloud Run deploy.

This is a pure adapter, not an HTTP route. Hosting service must separately
authenticate users and access the private GCS ledger with a read-only identity.
"""
from __future__ import annotations
from datetime import datetime
from research.three_model_evidence_gate import MODELS

ZH_MODEL={"bidirectional_intraday":"雙向當沖研究",
          "next_day":"隔日研究","swing_3_20d":"波段研究"}
ZH_DIRECTION={"LONG_WATCH":"偏多觀察","SHORT_WATCH":"偏空觀察",
              "NO_TRADE":"不交易"}

def _bar_time(row):
    bar_time=row.get("bar_time")
    if bar_time is None:
        # A rejected/no-trade item may not have any verified historical bars.
        # Do not replace missing bar time with workflow clock time.
        return None
    if not isinstance(bar_time,str):
        raise ValueError("invalid_bar_time")
    timestamp=datetime.fromisoformat(bar_time)
    if timestamp.utcoffset() is None:
        raise ValueError("bar_time_timezone_required")
    return timestamp.isoformat()

def project(records, *, max_records=100):
    if not isinstance(records,list) or not 1 <= max_records <= 500:
        raise ValueError("invalid_request")
    clean=[]
    ids=set()
    recognized=0
    rejected=0
    missing_bar_time=0
    for row in records:
        if not isinstance(row,dict) or row.get("model_id") not in MODELS:
            continue
        recognized+=1
        if row.get("production_signal") is not False or row.get("order_authorized") is not False:
            raise ValueError("research_ledger_contains_trade_authorization")
        if row.get("trained_model_used") is not False or row.get("eligible_strategy_trade") is not False:
            raise ValueError("research_ledger_status_mismatch")
        direction=row.get("direction")
        if direction not in ZH_DIRECTION:
            raise ValueError("invalid_direction")
        record_id=row.get("ledger_record_id") or row.get("signal_id")
        if not isinstance(record_id,str) or not record_id:
            raise ValueError("missing_ledger_record_id")
        if record_id in ids:
            raise ValueError("duplicate_ledger_record_id")
        ids.add(record_id)
        bar_time=_bar_time(row)
        if bar_time is None:
            missing_bar_time+=1
        reasons=row.get("rejection_reasons") or []
        if not isinstance(reasons,list) or any(not isinstance(x,str) for x in reasons):
            raise ValueError("invalid_rejection_reasons")
        if direction=="NO_TRADE":
            rejected+=1
        clean.append({
            "訊號編號":record_id,
            "模型":ZH_MODEL[row["model_id"]],
            "股票代碼":row["symbol"],
            "股票名稱":row.get("stock_name") or "待確認",
            "行情時間":bar_time or "待確認",
            "行情類型":"富果歷史K線，非盤中即時成交",
            "歷史參考收盤價":row.get("reference_close") if bar_time else None,
            "方向":ZH_DIRECTION[direction],
            "多方評分":None, "空方評分":None,
            "買進觸發":None, "最高接受價":None,
            "停損／失效":None,
            "現在動作":"觀察" if direction != "NO_TRADE" else "等待",
            "加碼價格":None, "停利價格":None,
            "拒絕原因":reasons,
            "資料狀態":"歷史K線已標註" if bar_time else "時間／資料待確認",
            "訊號資格":"研究觀察／非AI訓練訊號／禁止交易",
        })
    clean.sort(key=lambda row:(row["行情時間"] if row["行情時間"]!="待確認" else "",row["訊號編號"]),reverse=True)
    return {"schema":"sky-mobile-three-model-research-v2",
            "正式交易":False,"模型狀態":"尚未訓練或未驗證",
            "即時行情已驗收":False,"CloudRun已部署":False,
            "資料健康":{"研究紀錄總數":recognized,
                       "已標示不交易":rejected,
                       "缺行情時間":missing_bar_time,
                       "顯示筆數":min(len(clean),max_records),
                       "實際雲端頁面已驗收":False},
            "rows":clean[:max_records]}
