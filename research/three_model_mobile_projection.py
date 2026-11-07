"""Read-only mobile projection of validated research records.

This module does not create a public API route, authenticate clients, or deploy Cloud Run.
The hosting application must enforce authentication and retrieve objects using private IAM.
"""
from __future__ import annotations
from datetime import datetime
from research.three_model_evidence_gate import MODELS

ZH_MODEL={"bidirectional_intraday":"雙向當沖研究",
          "next_day":"隔日研究","swing_3_20d":"波段研究"}
ZH_DIRECTION={"LONG_WATCH":"偏多觀察","SHORT_WATCH":"偏空觀察",
              "NO_TRADE":"不交易"}

def project(records, *, max_records=100):
    if not isinstance(records,list) or not 1 <= max_records <= 500:
        raise ValueError("invalid_request")
    clean=[]
    for row in records:
        if not isinstance(row,dict) or row.get("model_id") not in MODELS:
            continue
        if row.get("production_signal") is not False or row.get("order_authorized") is not False:
            raise ValueError("research_ledger_contains_trade_authorization")
        if row.get("trained_model_used") is not False or row.get("eligible_strategy_trade") is not False:
            raise ValueError("research_ledger_status_mismatch")
        direction=row.get("direction")
        if direction not in ZH_DIRECTION:
            raise ValueError("invalid_direction")
        if not isinstance(row.get("signal_id"),str) or not row["signal_id"]:
            continue
        if not isinstance(row.get("bar_time"),str):
            raise ValueError("missing_data_time")
        datetime.fromisoformat(row["bar_time"])
        clean.append({
            "訊號編號":row["signal_id"],
            "模型":ZH_MODEL[row["model_id"]],
            "股票代碼":row["symbol"],
            "股票名稱":row.get("stock_name") or "待確認",
            "行情時間":row["bar_time"],
            "行情類型":"富果歷史K線，非盤中即時成交",
            "歷史參考收盤價":row.get("reference_close"),
            "方向":ZH_DIRECTION[direction],
            "多方評分":None, "空方評分":None,
            "買進觸發":None, "最高接受價":None,
            "停損／失效":None,
            "現在動作":"觀察" if direction != "NO_TRADE" else "等待",
            "加碼價格":None, "停利價格":None,
            "訊號資格":"研究觀察／非AI訓練訊號／禁止交易",
        })
    clean.sort(key=lambda r:(r["行情時間"],r["訊號編號"]),reverse=True)
    return {"schema":"sky-mobile-three-model-research-v1",
            "正式交易":False,"模型狀態":"尚未訓練或未驗證",
            "即時行情已驗收":False,"CloudRun已部署":False,
            "rows":clean[:max_records]}
