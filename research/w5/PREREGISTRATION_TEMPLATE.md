# W5 Pre-registration Template

> 僅限 W5 狀態為 ACCEPT_FOR_PREREGISTRATION 的 Candidate 使用。結果出來後不得用局部調參改寫本文件。

## 1. Research question
- Candidate：
- Primary hypothesis：
- Null hypothesis：
- Market：
- Universe：
- Horizon：

## 2. Data contract
- PIT universe source：
- Feature timestamp：
- Label timestamp：
- Corporate action handling：
- Missing-data policy：
- Leakage exclusions：
- Train range：
- Validation range：
- OOS range：
- Fresh OOS qualification：

## 3. Baselines
### Deterministic baseline
- Rule：
- Expected behavior：

### Linear baseline
- Model：
- Features：
- Regularization：

### Optional challengers
只有 deterministic + linear baseline 有證據後才可啟用：
- Random Forest
- XGBoost
- LightGBM

LSTM / Transformer / RL 預設禁止。

## 4. Signal / ranking
- Feature list：
- Ranking / trigger rule：
- Entry timestamp：
- Exit rule：
- Rebalance frequency：
- Top-N：
- Tie handling：

## 5. Execution / cost
- Primary round-trip cost：0.45%
- Stress round-trip cost：0.65%
- Slippage assumption：
- Liquidity filter：
- Capacity assumption：

## 6. Risk / portfolio
- Max concurrent positions：
- Position sizing：
- Single-symbol cap：
- Sector concentration cap：
- Correlation rule：
- Portfolio heat：
- Kill switch：
- Max DD threshold：

## 7. Required metrics
- After-cost Expectancy
- PF
- Max Drawdown
- Win rate
- Avg Win / Avg Loss
- MAE / MFE
- Turnover
- Ranking IC（若為 ranking）
- Calibration（若輸出 score/probability）
- Stability by fold
- Stability by regime
- Cost sensitivity
- Concentration
- Capacity
- Explainability

## 8. Validation
- Walk-forward folds：至少 3
- Regimes：Bull / Neutral / Bear
- Ablation plan：
- Portfolio validation：
- Capacity validation：

## 9. Promotion thresholds
在研究開始前固定：
- Minimum after-cost expectancy：
- Minimum PF：
- Max acceptable DD：
- Minimum OOS sample：
- Concentration threshold：
- Cost stress requirement：
- Shadow/Paper eligibility：

## 10. Stop conditions
任何一項成立即停止升級：
- PIT fail
- Leakage / survivorship fail
- OOS materially negative
- Cost stress collapse
- Concentration fail
- Capacity fail
- Regime catastrophic failure
- Result depends on post-hoc threshold search

## 11. Governance
- W5 outcome：
- W0 review required：YES
- Destination if approved：W1 / W2 / Other
- Production modification allowed：NO
