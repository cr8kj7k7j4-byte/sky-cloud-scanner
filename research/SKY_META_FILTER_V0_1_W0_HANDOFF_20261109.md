# W0／P0-G 交接｜Sky Meta-Filter V0.1 前瞻正式候選來源缺口

2026-11-09｜本研究僅工程 source preflight，**不是 W0／P0-G 正式核准文件**。

## 已核對實際來源

- `.github/workflows/scan.yml` 的 Workflow 名稱是 `Sky Cloud Scanner v0.5 + P0-R`，交易日預設掃描為 TPE 09:05／09:15／09:30／09:50／10:15。
- workflow 引用 `FUGLE_API_KEY`，有 TWSE 交易日驗證及 `PASS_FULL_MARKET_LIVE` 全市場資料覆蓋失敗即阻擋的安全規則。但**這些規則不是完整 v1.4 買進資格**。
- `src/decision_engine.py` 的 P0-C first_gate 只審查基本流動性與交易資格，不替代 v1.4 市場／相對強弱／MTF／行情階段／突破觸發／防追高等完整決策。
- `research/SKY_DAY_V14_FROZEN_RULE_SOURCE_REGISTRY.json` 與 W0 2026-10-26 治理文件仍標記 **10/10 v1.4 歷史規則 provider UNRESOLVED**；不得重建門檻或以 archived breakout 代理。
- CI `Sky Meta-Filter Research Contract CI (No Production)` 對真實 GitHub Workflow 與 registry 做 source preflight，輸出 `sky-meta-filter-forward-preflight-v0.1`，不可接入候選 `admitted_candidates=0`、`forward_private_ledger_enabled=false`、`production_change=false`。

## 明確的下一個 W0/P0-G 決策

1. 決定 **真正的 2026-11-09 起前瞻決策來源**（程式入口／工作流程／Git commit／不可變輸出位置），不可將現在的 scan ranking、P0-C first_gate 或研究訊號當正式 v1.4 買入訊號。
2. 確認正式候選**來源 ID 與凍結契約**：`decision_id`、`strategy_id`、`strategy_version`、`source_run_id`、`source_commit_sha`、`candidate_at`、`feature_cutoff_at`、`symbol`、`source_quote_at`、`source_quote_provider`、`candidate_pool_id`、全部 10 項 `canonical_rule_outputs`、`p0r_status`、`entry_trigger`、`original_stop`、`baseline_action`。
3. W3A 核對逐股行情時間、資料可得性及 PIT；W2 確認完整 10 項既有 v1.4 Alpha 規則可觀察，不能創造歷史不存在的規則；W6 提供反事實進出場成本與成交條件；W3B 提供獨立、權限受控、immutable 儲存。
4. 由 W0/P0-G **實際簽核**正式候選來源、研究 feature cutoff、Meta model frozen weights/threshold。此文件自身沒有任何認證權力。
5. 只有來源 Gate 經正式治理擴充並通過真正盤中 E2E 讀回後，才可讓 Meta shadow collector 寫入 ACCEPT、REJECT 與 PENDING。未獲核准期間維持 0 admitted，**不要默默產生研究用假候選**。

## 必須分開回報的驗收層級

| 層級 | 目前狀態 |
|---|---|
| 原始掃描 Workflow 存在 | PASS |
| 自動化來源稽核 CI | PASS |
| v1.4 完整正式決策來源已認證 | BLOCKED |
| Meta 真實分數／固定模型權重 | WAIT |
| Meta 候選不可變 GCS 入帳 | WAIT |
| 逐筆結果追蹤與成本後績效 | WAIT |
| 200 樣本／20 未來交易日／2 Regime／95% 完整率／20% 集中度 | WAIT |
| Production | UNCHANGED |

參考：PR #384，Issue #375，`research/sky_meta_filter_forward_preflight.py` 及該 PR 的成功 CI artifact。不可只靠 GitHub workflow 成功宣稱正式 Meta 模型完成。
