# Sky 100 Phase 10｜Champion vs Challenger Live Evaluation Dashboard

## 目的

Champion 與 Challenger 在相同盤中事件下同步產生 Shadow 訊號，以相同資料、成本與風控條件比較。

## 核心比較

- Expectancy R
- Profit Factor
- MFE R
- MAE R
- False Breakouts
- Missed Opportunities
- Risk Rejections
- Regime Performance

## Event Matching

同一 event_id 必須讓 Champion / Challenger 使用同一市場事件與資料時間，避免比較基準不同。

## Governance Review

Challenger 只有在：
- 樣本數足夠
- Expectancy 相對 Champion 有增益
- PF 相對 Champion 有增益
- 假突破沒有惡化
- 漏訊號沒有惡化
- Regime 一致性通過

才可進 Governance Review。

## 禁止

- Dashboard 不可自動替換 Champion。
- automatic_promotion_allowed 固定為 false。
- live_order_allowed 固定為 false。
- 不可把單一日、單一週或單一 Regime 優勢視為正式升版證據。
