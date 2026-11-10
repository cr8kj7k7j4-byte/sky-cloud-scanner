# W0｜全庫安全精簡第一批（2026-11-10）

## 決策

**僅移除已過期、且不再提供有效時間窗的 Workflow 入口。** Git 歷史、舊 Actions runs、研究程式、測試、正式策略及研究證據繼續保留。不藉由清理放寬行情、P0-R、成本後 RR、五分鐘 K 棒或 W0/P0-G 的 Gate。研究與 PAPER_ONLY 不需券商帳戶；實盤交易仍關閉。

## 當前 baseline（查核 main）

- Git tracked 全庫項目：895；檔案：866；Workflow：167；tests：199；src：93；research：290。
- 開放 PR：75（其中 Draft 61）。部分 PR 與已合併版本及同領域草稿重疊，**不能直接依年齡自動關閉**。
- 目前已找到兩個同時段五分鐘行情流程：
  - `.github/workflows/scan.yml`，負責當沖主掃描及研究資訊產出，但目前正式成交覆蓋 Gate 失敗。
  - `.github/workflows/sky-full-market-five-minute-dispatch.yml`，派送 `sky-full-market-private.yml` 寫入 GCS 的研究行情。
  - **此二者不可在未核對資料產出、依賴及費用前任意停用；最終目標是上游行情只取得一次，獨立區分市場觀察與正式交易證據。**

## 本批已移除的四個過期定時 Workflow

| Workflow 入口 | 原有時間限制 | 移除原因 |
| --- | --- | --- |
| `sky-overnight-readiness-watch-20261109.yml` | 台灣 11/09 14:00 起至 11/10 09:00 前 | 11/10 09:00 後只會輸出 expired，仍每 15 分鐘排程 |
| `sky-overnight-13col-acceptance.yml` | 台灣 11/10 09:00 截止 | 過期後每五分鐘空轉 |
| `sky-overnight-readonly-acceptance-20261110.yml` | 台灣 11/10 09:30 截止 | 已包含自行停用邏輯，移除過期入口、保留證據程式 |
| `sky-preopen-watch-20261110.yml` | 台灣 11/10 09:50 截止 | 已包含自行停用邏輯，過期且不再需此日期專用排程 |

**影響：167 → 163 個 Workflow 檔案；總檔案 866 → 862，另新增一個回歸測試與本份文件，實際主分支最終檔案數請以合併後重新讀取為準。** 不能以檔案數下降直接推算行情掃描加速比例。

## 保留與禁止動作

- 保留 `scan.yml`、`sky-full-market-five-minute-dispatch.yml`、`sky-full-market-private.yml`、`sky-chat-bridge.yml`、`schedule-health-audit.yml`、`sky-paper-only-acceptance.yml`、`sky-recovery-watchdog.yml`。
- 保留 `src/risk_engine.py`、`src/main.py`、`src/cost_profiles.py` 與 W6 #365、W3B #488、W3A #480 主責分支（目前 Draft）。
- 保留 `ops/preopen_readiness_watch.py`、`ops/recovery/sky_overnight_readonly_acceptance.py` 及其測試和 Git 歷史，以供回溯。
- 不移除任何 `ARCHIVED_NO_RETUNE` 研究證據；先前依治理封存的 15 個 Workflow 不重做。
- 不更動正式 09:00–13:30 五分鐘任務時段，不新開付費 API 請求，不新增 ChatGPT 排程，不自動下單。

## 開放 PR 去重判定

- `#365`：W6 風控整合主線（保持 Draft，不可直接當作 Production 成功）。
- `#253`、`#265`：與 #365 的兩筆停損硬性阻擋明顯重疊；建議關閉舊提案並在 PR 註明「由 #365 整合」，**不移除歷史程式差異**。
- `#355`：也屬兩筆停損、成本 Gate 領域，須逐項檢查是否有 #365 未保留的獨立測試後才能關閉。
- `#421/#437/#430/#435/#432/#438`：多個 13 欄呈現研究；不得批次合併，因不同指令及資料路由仍可能有差異。正式 13 欄契約需由 W0 統一。
- `#480/#488/#357` 等：成交證據與因果 Gate 主線，應維持獨立研究驗收。
- `#373`：早期五分鐘排程 PR 同時新增歷史 markout/replay 模組，並非只有重複 cron，不能未拆功能就關閉。

## 驗收與下一批

1. 研究凍結 CI 與本批 4 項回歸測試綠燈、合併讀回。
2. 確認沒有將已移除的日期專用入口作為正式依賴。
3. 下一批優先找「到期後仍繼續執行、但不產生資料價值」的暫時性 cron。
4. 每條付費行情 Workflow 必須取得最新成功/失敗 Run、消耗路徑、實際資料欄位、下游引用、通知及重試證據，才能合併或停用。
5. 最後評估執行時間、重複行情請求數、GitHub Actions 使用情況；未取得基準與後測，不聲稱已加速。

**結論：精簡入口可降低過期排程負擔，但 167 個 Workflow 的數量不是唯一瓶頸。真正的主要阻礙仍是正式行情 Gate、P0-R 治理與資料鏈重複查詢；保持 NO_LIVE_TRADING。**

## 第二批（2026-11-10，另行 CI 驗收）

在第一批合併後，繼續依程式內明確截止時間處理：

- 移除 `.github/workflows/sky-preopen-evidence-monitor.yml`：臨時盤前 Read-only 監控截止 2026-11-10 10:30 台灣時間，內含自動停用邏輯；保留 Git 歷史及故障證據。
- 從 `.github/workflows/sky-research-ci-watchdog.yml` 移除 `*/5 * * * *` 排程：原 24 小時研究 CI 監控截止 2026-11-10 04:00 UTC（12:00 台灣），保留 PR 單元測試與手動診斷入口。
- 從 `.github/workflows/w2-research-24h-watchdog.yml` 移除 `*/5 * * * *` 排程：原監控截止 2026-11-09 02:38 UTC，保留 W2 的 PR 回歸測試與手動診斷入口。
- **不要誤認「每五分鐘 cron 從 YAML 消失」等於 GitHub 已證實未來不再觸發**：合併後須讀回 main，後續在交易日核對 schedule 事件記錄。
- 第一批去重 PR：關閉 #253、#265（保留歷史），由 W6 #365 負責兩筆停損硬阻擋的正式整合；#365 仍是 Draft、不得提升 Production。
- 僅憑歷史檔案/Workflow 數量無法證明效能改善。**評估標準**是停止過期 cron、保留正式掃描/告警、降低重複事件與 API 查詢，並逐步測量 Actions 使用量。實際省下多少 Actions 分鐘與付費額度待觀察。

**本次兩批不修改 `scan.yml` 與 `sky-full-market-five-minute-dispatch.yml`，因為它們都在執行與尚待正式驗收的資料來源工作；直接關閉任一條可能使資料更不完整。**

## 第三批（2026-11-10）：過期一次性雙重掃描與 AI 24h 排程

- 已核實 `.github/workflows/sky-research-once-20261109.yml` 是特定日期的手動研究驗收入口；執行時**同時發起** `scan.yml` 與 `sky-full-market-private.yml`，不是獨立不可替代的正式資料產出者。兩個下游仍由既有 Workflow 可用；移除舊入口避免人員重複觸發付費行情。Git 歷史可查。
- `.github/workflows/ai-direction-watchdog-5m.yml` 的研究 24h 偵測窗明定截止 2026-11-09T02:38:00Z；已移除 `*/5 * * * *`，保留 `workflow_dispatch` 的研究診斷，其他模型及證據不動。
- 兩條正式市場的五分鐘掃描 Cron、GCS、PAPER_ONLY、W0/ P0-G 規則不變。**沒有再次觸發付費行情或建立新排程**。
- 研究策略家族 `ARCHIVED_NO_RETUNE` 的程式和歷史驗證文件不可因本批清理而刪除。
- PR 去重僅對經 patch 比對確實已被主線覆蓋的項目執行關閉並留言保留歷史；未審過的候選仍保留。
