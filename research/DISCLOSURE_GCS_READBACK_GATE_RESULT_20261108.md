# 2026-11-08 GCS 證據長期保存｜建置及驗收結果

**判定：LOCAL_GATE_PASS / GCS_E2E_NOT_VERIFIED，RESEARCH_ONLY。**

## 基礎
- 官方來源採集 PR #322，4/4來源在 Run #42417888034 成功、原始 bytes + SHA256 已保留在短期 artifact。
- 本次堆疊 PR #326：https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/326
- GitHub Actions Gate：https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42418393935
- 5 項單元測試全 PASS（包括四來源資料清單、雜湊竄改、資料缺漏、非法 run id、重複寫入拒絕）。
- CI `unit` SUCCESS；`store` SKIPPED，因為不允許 PR 工作流攜帶雲端權限（真正寫入只允許 `workflow_dispatch`）。
- **沒有使用 GCS 真實身分登入、寫入或讀回；不得把本地 mock bucket 的成功當成雲端保存驗收成功。**

## 安全實作
- 以 Google Workload Identity Federation 短期憑證取代長期 JSON Key。
- GitHub Repo Var `DISCLOSURE_GCS_BUCKET`，Secrets `DISCLOSURE_GCP_WIF_PROVIDER`／`DISCLOSURE_GCP_SERVICE_ACCOUNT`。可否取得這些設定與 GCS IAM，目前 GitHub 連接器未提供可讀取驗證的工具，**待確認**。
- 只允許四個官方資料與證據 manifest、hash、UTC 首次觀測時間；**不轉存富果付費行情**。
- 用 `if_generation_match=0` 保護單次寫入避免覆寫既有物件；每一份上傳後重新下載，逐 byte 比對，再寫入 manifest commit marker。用 `run_id`+ `attempt` 隔離不同執行。
- **create-only app logic != GCS bucket retention 或 immutability**：桶存留期/版本/不可變更設定、IAM 最小權限、通知及失敗警報未驗證。
- 沒有 cloud credential 時 must fail-closed，不會「回退」到未受保護的公開桶。

## 要讓它真正運作而不是只通過單元測試的最短路徑
1. 有權限的人查看 Google Cloud 實際 bucket、GCS retention rule、服務帳戶及 GitHub WIF trust policy；設定或確認上述 GitHub Secret/Var（不要在聊天貼憑證）。
2. 審查 PR #322/#326，確認雲端授權符合限制；依序合併基礎 PR 與堆疊 PR。
3. 在已審核版本從 GitHub Actions `workflow_dispatch` 手動執行，檢查 4/4來源、5個物件 GCS 寫入／重新讀回、manifest SHA 一致、失敗告警及可查報告的取得方式。
4. 在多個實際交易日驗證存取成功率、時間、源資料錯誤、重覆與長期保存；完成前**不新增 cron**。
5. 資料合格仍只能代表 `observed_at`，不能反推真實各公司 `published_at`。研究中 Revenue MoM 5D、財報事件策略仍受歷史公告時間 PIT Gate 阻擋。
6. 完整富果歷史行情已於 PR #321 檢查，後續僅在合格事件的獨立 OOS/前瞻資料上做成本後策略回測；所有升版經 W0/P0-G 審查。

## 結論
資料保全的**程式／單元測試** PASS；
正式 GCS 端到端、保留政策、WIF IAM **尚待驗證**；
正式事件資料公開時間與正期望 **未通過**；
Production、Cloud Run 與定時排程均未改變。
