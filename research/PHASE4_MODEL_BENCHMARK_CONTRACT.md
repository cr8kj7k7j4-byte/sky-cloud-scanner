# Sky 100 Phase 4｜Model Benchmark Arena

## 目的

把所有候選模型放在相同資料、相同時間切分、相同交易成本與相同升版規則下比較。

## Production Arena V1

- Sky Rule Engine
- Logistic Regression
- Random Forest
- XGBoost
- LightGBM

LSTM 與 Reinforcement Learning 暫留研究池。

## 統一比較指標

- OOS 扣成本後 Expectancy
- Profit Factor
- Maximum Drawdown
- Stability Score
- Trade Rate
- Positive Trade Rate（描述性統計，不是實際上漲機率）

## 硬性升版門檻

只有全部通過才可標記 Production Eligible：

- OOS Net Expectancy > 0
- PF > 1
- MDD 未超過治理門檻
- Walk-forward 通過
- Cost Stress 通過
- Leakage Check 通過
- Survivorship Review 完成
- Regime Robustness 通過
- Paper Trading 通過

## 禁止

不得因 Accuracy 最高、單一月份最佳、單一 Regime 最強或單次回測結果漂亮而直接成為 Champion。
