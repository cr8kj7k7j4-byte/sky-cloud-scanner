# Sky 100 Roadmap

> 「100 分」定義為工程與驗證成熟度目標，不代表勝率、獲利率或未來報酬保證。

## Production pipeline

P0-A Data Engine
→ P0-B Feature Engine
→ Scanner
→ P0-C Decision Engine
→ P0-R Risk & Portfolio Engine
→ P0-E Alert / Execution Assistance
→ P0-L Trade Logger
→ P0-D Learning & Validation
→ P0-M Model Registry

## 已具備

- TWSE / TPEx 官方母池與來源健康檢查
- Fugle 深查介面
- Feature Engine 基礎欄位
- Market Regime
- Rule / Decision Engine
- P0-R Risk Engine
- ML baseline contract
- Validation Gate
- Backtest / OOS research workflows

## 本階段新增

- P0-M Model Registry：Champion / Challenger，不允許未驗證模型升 Production
- P0-L Trade Logger：交易成本、MFE、MAE、R Multiple、持倉時間
- Engineering Readiness：把「100 分」改成可稽核的工程門檻
- GitHub Actions：核心模組每次 PR 自動測試

## 仍未完成，不得宣告 100%

1. TPEx 嚴格官方盤中全市場資料鏈
2. Feature Store schema/versioning 與資料品質監控
3. 正式模型訓練（RF/XGBoost/LightGBM）及固定資料切分
4. Walk-forward + OOS + regime 分層完整驗證
5. Cost/slippage stress matrix
6. Look-ahead / survivorship / leakage 自動檢查
7. Paper Trading 累積樣本
8. Alert delivery monitoring / retry / dedup
9. Dashboard / Mobile API
10. Production model promotion / rollback SOP

## 模型升版原則

任何 Challenger 只有在以下全部通過後，才可成為 Champion：

- Walk-forward 通過
- OOS 通過
- 成本壓力測試通過
- 資料洩漏檢查通過
- Paper Trading 通過
- 扣除交易成本後 Expectancy > 0
- PF 與 MDD 達預先定義門檻
- 跨 Market Regime 無單一區段災難性失效

不得因單次回測較漂亮、單一月份獲利、或 Accuracy 較高就直接升 Production。
