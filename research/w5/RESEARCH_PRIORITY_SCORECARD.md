# W5 Research Priority Scorecard

> 用途：只在 Candidate 通過 Duplicate / Low-value Gate 後使用。分數不是勝率，也不是預期報酬。

每項 0–2 分：

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Known gap fit | 與已知缺口無關 | 部分相關 | 直接補核心缺口 |
| PIT feasibility | 不可得 | 不確定／需補 | 可驗證且歷史可重建 |
| OOS feasibility | 無 untouched OOS | 有限 | 可保留真正 untouched OOS |
| Economic logic | 無 | 弱／間接 | 清楚、可證偽 |
| Production relevance | 低 | 中 | 高 |
| Complexity | 高且黑盒 | 中 | 低且透明 |
| Cost robustness | 高換手／高度敏感 | 中等 | 成本合理 |
| Capacity | 容量不明／很差 | 中等 | 可驗證且合理 |
| Explainability | 低 | 中 | 高 |
| Structural novelty | 無 | 部分 | 明確新 target/data/execution/framework |

總分滿分 20。

## Interpretation
- 16–20：High priority，但仍需完整 Pre-registration。
- 11–15：Medium priority，視 W0 研究資源排序。
- 6–10：Low priority，通常 HOLD。
- 0–5：通常 REJECT_LOW_VALUE 或 ARCHIVE。

## Hard gates override score
以下任一成立，不得因總分高而通過：
- Duplicate frozen family without structural difference
- PIT FAIL
- No untouched OOS
- Leakage not controllable
- Only parameter retuning
- Execution infeasible
