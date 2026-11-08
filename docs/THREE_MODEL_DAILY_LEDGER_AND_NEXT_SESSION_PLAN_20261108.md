# Sky 三模型：每日研究入帳＋下個交易日市場觀察（2026-11-08）

**Status: REVIEW_ONLY / NOT SCHEDULED ON MAIN / NOT PROMOTED.** This PR defines a bounded two-symbol research collection workflow, not six trained AI models and not executable trading instructions.

## 目前可核對基準

- 實際 Fugle 1101、8088 三研究類型共 6 個私有 GCS 觀察物件曾通過 create-only / readback / 重跑相同 hash 驗收，詳見 2026-11-08 成功的 GH runs 42429510286、42429767999。
- 手機端 Cloud Run canary Revision `tw-ai-mobile-00157-wiw` 已由使用者截圖證實六筆、股票名稱與中文拒絕原因可讀，**正式 Revision `00154-csh` 仍承接 100% 流量**。這不是未來資料持續入帳的證據。
- `.github/workflows/three-model-fugle-private-ledger.yml` 原本 **僅 workflow_dispatch**，不能稱為已啟用的每日研究掃描。
- `.github/workflows/shadow-outcome-backfill.yml` 使用既有 P0-C 之 paper/Shadow 紀錄，**不是**三模型 `ledger_record_id` 的 T+1 結果管線。

## 待審查的研究排程

| Workflow | cron (UTC) | 台灣時間 | 限制 |
| --- | --- | --- | --- |
| Three Model Research Daily Dispatcher → Fugle Private Ledger | `30 9 * * 1-5` | 週一～週五 17:30 | dispatcher 透過 GitHub API 觸發 main `workflow_dispatch`；1101、8088；當日日 K 與 5m 必須都有當日時間才寫入；每日最多 6 筆（含 NO_TRADE） |
| Three Model Research Daily Dispatcher → Next Session Markout | `30 10 * * 1-5` | 週一～週五 18:30 | dispatcher 觸發 main `workflow_dispatch`；私有 GCS 的下個實際交易日 D close；Immutable followup prefix |

- 週末不排程。休市日／停牌／Fugle 不完整回應不直接猜測：資料時間覆蓋不足則不寫入新觀察，摘要 `SKIPPED_SESSION_COVERAGE_UNCONFIRMED`（不等於已確認官方休市）。實際是否為台股交易日尚待官方 TWSE/TPEx 行事曆交叉驗證。
- 同一日期重新執行使用既有 `if_generation_match=0`、讀回 SHA256 和 `ALREADY_EXISTS_IDENTICAL`；任何不同版本覆蓋同一 ID 必須失敗，不能偷偷替換。
- 次日回填寫在不同的 `three-model-followup/v1/` 私有前綴，不會被手機研究帳本誤當作研究訊號。必須有嚴格較晚的已完成日 K 交易日才會寫入；不能把當天價當事後結果。
- markout 是**可觀察收盤價變動**，不表示已觸發、可放空、可借券、成交、滑價、停損／停利、成本後獲利或正期望值。對 NO_TRADE 也可做市場事實觀察，但不得納入策略交易樣本。
- 單次回填最多掃描 20,000 個私有原始 JSON（2 檔 × 3 類型在全部交易日均入帳時，約可涵蓋多年，但非無限）；超限 fail closed；超過 29 日未取得後續觀察的紀錄保留 pending，須另設長期研究保全與分頁治理才可擴張，不能宣稱永久完整收集。空的下一交易日 K 線則保持 pending，不當成錯誤成交。
- Fugle API key 仍採 GitHub secrets，不寫入 log／PR；GCP 以 WIF/OIDC 身分驗證，不新增 JSON key；研究 Bucket 私有且不重用 disclosure Bucket。

## 排程啟用前的硬性阻礙

1. 本 PR 目前研究分支，不會觸發主分支排程；且 **排程預設 OFF**：dispatcher 的 schedule job 需要 repo Actions Variable `SKY_THREE_MODEL_SCHEDULE_ENABLED=true` 才執行；未設定時 job SKIPPED、沒有付費 API 呼叫。主分支手動 dispatcher `workflow_dispatch` 可以作為一次性驗收，不受此 flag 影響。須經 W0 審查、合併與人工觸發驗收後再審慎設定 flag，且首次定時觸發依然需要查看 run ID；**不能以 Workflow 有 cron 便宣稱已排程成功。**
2. **不改動 GCP Workload Identity Provider 的 attribute condition**。既有文件明確只允許 `main + workflow_dispatch`。新增的 **無 GCP 權限** `three-model-research-daily-dispatch.yml` 用 GitHub Actions `actions:write` GITHUB_TOKEN 僅 dispatch 指定的兩個 main 研究 workflow；下游由 `workflow_dispatch` 取得原 WIF 身分。必須先審核 dispatcher 權限及 GitHub Token dispatch 行為，在 main 確認實際 schedule → dispatch → WIF 的 run chain 成功後才稱排程啟用驗收通過。不能拓寬 provider 到 `schedule`、不得建立 JSON key。
3. 確認 WIF 身分有研究 Bucket 的 objectCreator、objectViewer 及 list 權限，並能在新 prefix 寫入；目前已證實原研究紀錄寫入，不代表新 outcome prefix 的執行結果已通過。
4. GitHub repo Actions workflow permissions 必須允許 `GITHUB_TOKEN` 的 `actions:write` dispatch；由 GitHub audit 記錄 17:30 / 18:30 兩次派送 run ID。兩條排程首次實際 run 後，核對 run ID、使用者查看方式、排程 UTC/TPE、Fugle 的最後交易日、是否跳過休市日、create-only 物件數與 hash、模型數、唯一 ID、NO_TRADE 及缺失時間數量；下一交易日才核對有實際後續行情的 markout。
5. GitHub Action error 由 GitHub run failure 顯示，但「使用者會收到通知」尚未證實，需核對通知設定。取消／重複排程、跨日補跑、完整性≥95%、至少 200 獨立樣本／20 未來交易日／兩個 regime 都尚未完成。
6. 無須更新 Cloud Run 正式流量、無須啟用 Production／自動下單。升級須 W0/P0-G 治理；研究觸發不是正式交易買賣資格。

## 驗收狀態字典

`CODE_PASS`（CI）≠ `SCHEDULE_CONFIGURED` ≠ `SCHEDULE_TRIGGER_OBSERVED` ≠ `PAID_DATA_RECEIVED` ≠ `GCS_WRITE_READBACK` ≠ `NEXT_SESSION_OUTCOME` ≠ `MODEL_VALIDATED` ≠ `PRODUCTION_ELIGIBLE`。

**目前可宣稱：研究程式與排程候選已提交 PR。不能宣稱啟用、下一日已入帳、或驗證了正期望值。**
