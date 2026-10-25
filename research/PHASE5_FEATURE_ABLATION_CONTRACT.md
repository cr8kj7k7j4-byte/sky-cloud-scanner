# Sky 100 Phase 5｜Feature Importance + Ablation Lab

## 目的

Phase 5 用來回答「哪些 Feature / Gate 真正增加策略價值」。

重要原則：

- Feature Importance 不等於因果。
- 單次 Importance 高，不得直接保留。
- 單次 Ablation 變差，也不得直接升正式規則。
- 所有結論必須進一步通過 Walk-forward、OOS 與 Market Regime 一致性驗證。

## V1 Feature Groups

- Momentum：ret_1 / ret_3 / ret_5
- Volatility：vol_5 / vol_20 / range_pct
- Volume：volume_ratio_5
- Price vs Avg：close_vs_avg_pct

## 固定研究方法

1. Full Model 建立基準
2. Permutation Importance
3. Single Feature Ablation
4. Feature Group Ablation
5. 比較 Net Expectancy / PF / MDD
6. 進行 Walk-forward 一致性檢查
7. 進行 Regime 一致性檢查
8. 最後才進 Governance Decision

## Governance Status

- KEEP：跨 Regime + Walk-forward 均有增益證據
- RESEARCH_MORE：證據混合，不得改 Production
- PRUNE_CANDIDATE：移除後整體反而改善，可列刪除候選

任何 Feature / Gate 的刪除仍需重新完整回測，不可因單一實驗直接上線。
