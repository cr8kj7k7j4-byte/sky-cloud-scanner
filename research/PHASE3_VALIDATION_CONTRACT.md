# Sky 100 Phase 3｜Validation & Model Research Contract

Phase 3 目標是建立可重現、樣本外、扣除交易成本後仍可驗證的研究流程。

## 固定驗證層
1. Time-based Train / Validation / OOS
2. Walk-forward
3. Cost + Slippage Stress Matrix
4. Look-ahead / Leakage Audit
5. Survivorship-bias Review
6. Market Regime 分層
7. Feature Importance
8. Ablation Test
9. Paper Trading
10. Champion / Challenger Promotion Gate

## Production Arena V1
- Sky Rule Engine
- Logistic Regression
- Random Forest
- XGBoost
- LightGBM

LSTM / RL 暫留 Research Pool。

## 正式升版最低條件
- Walk-forward 通過
- OOS 通過
- Cost Stress 通過
- Leakage Audit 通過
- Survivorship Review 完成
- Paper Trading 通過
- 扣除成本後 Expectancy > 0
- PF > 1
- 最大回撤符合預先定義門檻
- 主要 Market Regime 不可出現災難性失效

Accuracy、單月績效或單次回測不得單獨作為升版依據。
