# Sky 100 Phase 9｜Paper Trading + Shadow Deployment Engine

## 目的

Challenger 使用真實盤中資料平行運行，但禁止送出任何正式委託。

## 硬性原則

- live_order_allowed = false
- Shadow 只能記錄訊號與模擬結果
- 不得因 Shadow 單日或單週表現直接升 Production
- 每筆交易必須可回溯 strategy/model/feature/rule version

## 每筆 Shadow Trade 必須紀錄

- Symbol / Side
- Strategy Version
- Model Version
- Feature Schema Version
- Rule Configuration Version
- Signal Time / Source Time
- Entry / Stop / Target
- Quantity
- Regime / Setup / Phase
- Exit / Exit Reason
- Fees / Tax / Slippage
- Net P&L
- R Multiple
- MFE / MAE
- Holding Time

## Shadow Promotion Gate

研究初版至少檢查：
- 樣本數
- Expectancy R
- Profit Factor
- Max Drawdown R
- MAE tail risk
- Regime coverage
- Monitoring health
- Data quality

Shadow Gate 通過只代表可送進 Governance Review，不代表可以自動升 Production。
