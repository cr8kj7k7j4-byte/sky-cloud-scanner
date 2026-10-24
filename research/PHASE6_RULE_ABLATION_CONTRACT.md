# Sky 100 Phase 6｜Rule / Gate Ablation Lab

## 目的

把交易規則本身當成可驗證元件，而不是不可質疑的固定信念。

V1 Gate：
- Market Gate
- Sector / Relative Strength Gate
- Anti-Chase Gate
- Phase Gate
- Setup Gate
- Trigger Gate
- RR Gate

## 固定方法

1. Full Rules 建立基準
2. 一次關閉一個 Gate
3. 比較：
   - Expectancy（R）
   - Profit Factor
   - Maximum Drawdown（R）
   - Trade Count
   - Regime 分層
4. 再做 Walk-forward 一致性
5. 檢查樣本量
6. 才進 Rule Governance

## 治理狀態

- KEEP：有正貢獻，且跨 Regime、Walk-forward、樣本量均通過
- RESEARCH_MORE：證據混合
- PRUNE_CANDIDATE：拿掉後整體改善，可進入刪除候選

## 禁止

- 單次 Ablation 不能直接刪除 Production Gate。
- 不因交易次數增加就判定更好。
- 不因勝率提高就判定更好。
- 任何 Gate 變更後都必須重新完整回測、成本壓力與 Paper Trading。
