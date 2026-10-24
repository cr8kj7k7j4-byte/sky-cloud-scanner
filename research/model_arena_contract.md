# Sky Model Arena V1

Model Arena 用來比較不同模型是否值得升級，不用來宣稱「AI 勝率」。

## V1 候選模型

- Sky Rule Engine
- Logistic Regression
- Random Forest
- XGBoost
- LightGBM

## 固定驗證門檻

任何模型只有在以下全部通過時，才有資格進入 Champion 排名：

- Walk-forward
- OOS
- Cost stress
- Leakage check
- Paper Trading
- 扣除成本後 Expectancy > 0
- Profit Factor > 1

## 排名原則

優先考慮：

- Expectancy（R）
- Profit Factor
- 最大回撤
- 跨區段穩定性

Accuracy、單期報酬、單月績效不得單獨作為升版依據。

## 注意

LSTM / Reinforcement Learning 暫不納入 V1 Production Arena。
在 Feature Store、樣本外驗證與 Paper Trading 尚未成熟前，僅可放研究池。
