# Sky 100 Phase 6｜Rule / Gate Ablation Lab

## 目的

把交易規則本身當成可驗證元件，而不是不可質疑的固定信念。

本契約適用於 W2｜Sky 當沖驗證實驗室。Production Baseline 仍為
`Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP`；
任何 Ablation 結果均不得自行修改 Production。

## V2 固定 10-Rule Ablation Set

以 Full Model 為基準，一次只移除一條 Rule：

1. Market Gate
2. Sector / Relative Strength
3. Multi-timeframe Confirmation
4. Phase
5. Setup
6. Trigger
7. Anti-Chase
8. RR Gate
9. Opportunity Ranking
10. Execution Adjustments

Canonical columns:

- `market_gate`
- `sector_rs_gate`
- `multi_timeframe_gate`
- `phase_gate`
- `setup_gate`
- `trigger_gate`
- `anti_chase_gate`
- `rr_gate`
- `opportunity_ranking_gate`
- `execution_adjustment_gate`

## 固定方法

1. Full Rules 建立基準。
2. 一次關閉一個 Gate；禁止多條 Rule 同時變更後宣稱單一 Rule 貢獻。
3. 每條 Rule 至少比較：
   - n
   - Win Rate
   - Avg Win
   - Avg Loss
   - Expectancy（R）
   - Profit Factor
   - Maximum Drawdown（R）
   - MAE
   - MFE
   - R Multiple
   - Trigger frequency
   - False breakout rate
   - Slippage sensitivity
   - Cost-adjusted return
   - Sample Reduction
4. 必須再做 Walk-forward 一致性。
5. 必須做 Market Regime 一致性。
6. 必須檢查固定研究維度：
   - OOS
   - Market Regime
   - Time-of-day
   - Liquidity
   - Spread
   - Slippage
   - Trigger Quality
   - False Breakout
   - Missed Entry
   - Execution-adjusted RR
   - Ranking decile
   - Capacity
   - Sector concentration
   - Single-symbol concentration
7. 至少同時報告：
   - 0.45% primary round-trip cost
   - 0.65% stress round-trip cost
8. 只有完整 PIT / leakage / survivorship gate 通過後，才可將數值解讀為 Rule contribution。

## Rule Contribution 定義

每條 Rule 固定輸出：

- Expectancy Contribution
- PF Contribution
- Drawdown Protection
- Sample Reduction
- Fold Stability
- Regime Stability

Interpretation:

- Expectancy Contribution > 0：保留該 Rule 後，Full Model 的 after-cost Expectancy 較高。
- PF Contribution > 0：保留該 Rule 後，PF 較高。
- Drawdown Protection > 0：拿掉該 Rule 後 DD 惡化，表示該 Rule 具風控價值。
- Sample Reduction：該 Rule 阻擋的樣本數／比例；不得把單純減少交易誤稱為 Alpha。
- Fold / Regime Stability：只評估方向一致性，不等於真實勝率或未來機率。

## 治理狀態

- `STABLE_RULE`：after-cost Expectancy / PF 或 DD Protection 具可重複貢獻，且 Walk-forward、Regime、成本壓力均一致。
- `MIXED_RULE`：樣本足夠，但貢獻方向跨 fold / regime 不一致。
- `NEGATIVE_RULE`：拿掉後整體結果穩定改善，且無獨立風控價值。
- `INSUFFICIENT_DATA`：PIT、樣本、成本、欄位或 outcome 不足。
- `PRUNE_CANDIDATE`：僅為送 W0 審查的刪除候選，不得由 W2 直接移除 Production rule。

## Fail-Closed 原則

以下任一情況發生時，不得產生「Rule 有效」結論：

- 缺少 point-in-time feature timestamp；
- 使用 current-only sector mapping 回填歷史；
- 使用 future bars、MFE/MAE、exit outcome 建構入場 feature；
- 0.45% / 0.65% after-cost outcome 無法重建；
- execution timestamp causality 無法驗證；
- mandatory coverage < 95%；
- OOS 被反覆用於局部調參。

此時狀態固定為 `INSUFFICIENT_DATA` 或 `BLOCKED`。

## 禁止

- 單次 Ablation 不能直接刪除 Production Gate。
- 不因交易次數增加就判定更好。
- 不因勝率提高就判定更好。
- 不以 threshold、Top N、stop/target、indicator period、feature weight 微調救活 `ARCHIVED_NO_RETUNE` 家族。
- Counterfactual outcome 不得描述為真實成交或真實損益。
- 任何 Gate 變更後都必須重新完整回測、成本壓力與 Paper / Shadow 驗證。
