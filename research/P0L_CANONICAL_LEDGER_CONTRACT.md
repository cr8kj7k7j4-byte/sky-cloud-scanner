# P0-L｜Canonical Trade Ledger Contract

## 唯一正式入口

P0-L Canonical implementation：

- `src/trade_logger.py`

相容入口：

- `src/trade_log.py`：只保留 legacy re-export，不再維護獨立 schema。

Outcome 計算：

- `src/outcome_engine.py`：只負責結果計算，不負責另一套 ledger。

## Canonical Schema

`TRADE_LEDGER_SCHEMA_VERSION = 2.0.0`

Ledger 分成三層：

1. Decision
   - record_id
   - observed_at
   - run_id
   - symbol
   - decision
   - market/data quality/features/model/risk/plan/execution

2. Trade
   - side
   - entry/exit
   - quantity
   - initial stop
   - fees/tax/slippage
   - strategy/model/feature/rule version
   - decision_record_id

3. Outcome
   - gross/net P&L
   - R multiple
   - MFE/MAE amount
   - MFE/MAE in R
   - holding time
   - outcome status

## Compatibility

舊研究程式可繼續：

`from src.trade_log import build_trade_decision_record`

但實際實作會轉由 `trade_logger.py`。

## 治理原則

- 不允許 trade_log.py 與 trade_logger.py 各自演進 schema。
- outcome_engine.py 不再持有獨立 ledger。
- 新增欄位只能先加到 canonical schema，再由 adapter 暴露。
- 回測、Paper Trading、Shadow、實盤複盤必須使用同一 P0-L schema。
