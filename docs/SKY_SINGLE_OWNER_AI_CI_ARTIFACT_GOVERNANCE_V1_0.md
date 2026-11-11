# Sky W0/P0-G 單人治理與免費安全驗收契約 V1.1
日期：2026-11-11。模式：FREE_STATIC_SECURITY_REVIEW。狀態：PROPOSED，合併與強制執行狀態以 GitHub main、Branch Ruleset 和實際 Actions 為準。

## 適用範圍
適用於 Sky 所有模型、資料、研究、風控、執行模組、指令、文件、CI、Workflow 與自動修復 PR。此契約是橫向治理要求，不取代 `SKY_SYSTEM_REGISTRY_V2_1.md`、`research/RESEARCH_FREEZE_REGISTRY.md` 和 `docs/SKY_VALIDATION_PROTOCOL_V1_0.md` 的資料與研究 Gate。

## 角色、責任與核准
- 唯一 GitHub 維護帳號為 W0/P0-G 正式決策者。取消任何「非 PR 作者的 GitHub reviewer 必須 APPROVED」、「至少兩個不同帳號」、「第二帳號共同簽核」的強制條件。
- 單人治理不是自動核准。PR 記錄 `OWNER_GOVERNANCE_DECISION`、決策帳號、UTC 時間、完整 head SHA、範圍、證據 URL、未解風險、決策結果。允許 `HOLD | REJECT | APPROVE_SCOPE_ONLY`。
- 本專案採用免費規則式安全預檢與既有 GitHub CI。**沒有啟用真正的 AI/LLM 安全審查**；報告必須標示 `AI_REVIEW_NOT_ENABLED_FREE_MODE`，不得使用 `AI_PASS` 或宣稱模型已執行。W0/P0-G 決策由單一擁有者明確記錄，不能由規則式測試代簽。
- 不得使用 AI 自行同意其自身提出的程式修改、略過失敗 CI、偷偷改動 Branch Protection 或自動 merge。

## 強制證據：同 SHA / 同執行鏈
1. 準確記錄 PR head SHA 與基底 main SHA；每次 push 都重置審查、CI、Artifact 的有效性，禁止讀取舊 SHA 結果。
2. CI 必須由可信工作流程實際執行：單元、靜態檢查、權限/Secrets/注入安全、資料因果性及相應模組測試。成功須有該 SHA 的 run id、conclusion、workflow URL 與日誌證據。
3. 免費規則式安全預檢檢查修改的 Workflow 權限、`workflow_run` 信任邊界、Secrets、命令注入、供應鏈、交易/Production 意外啟動、API 費用與重複排程。此類檢測不具備 AI 推論能力；檢出敏感項目須保留 W0 人工判定，高風險或未解問題一律 HOLD。
4. Artifact 由實際 GitHub Actions run 產生，留存 run id、head SHA、產生時間、檔名、摘要/雜湊、下載及實際讀回結果。僅宣告已上傳、不下載讀回，不算通過。
5. 自動修補 E2E 必須追蹤來源失敗 Run → 來源 PR 同 SHA → 事件觸發 → 限定白名單修補 → 新 Draft PR/新 SHA → 下游 CI → Artifact 讀回。沒有真實失敗事件不可用 mock 宣稱 E2E PASS。
6. 行情與交易模組另須有真實來源時間、Snapshot/Quote/K 棒的因果驗證、成本後 RR、P0-R 風控、Paper 帳本完整性；CI PASS 不代表行情或交易 Gate PASS。

## Gate 判定
- `PASS`：同 SHA 的必要證據齊全，規則式安全預檢沒有未解高風險，CI 全綠，Artifact 真正讀回，W0/P0-G 明確記錄範圍決策。**此 PASS 僅指免費治理驗收，絕不表示 AI 模型審查通過。**
- `HOLD`：缺少必要規則式檢查或客觀證據、CI/Artifact 無權限、Workflow 未觸發、SHA 不一致、仍為 Draft、或適用的真實 E2E 尚未完成。未啟用 AI 應誠實標示，不能單憑這點冒充已通過 AI；若某研究或發布規範明定必須 AI 模型審查，該範圍仍 HOLD。
- `REJECT`：已確認資安/資料/風控 Gate 不合格，或不可接受的修補風險。
- `APPROVE_SCOPE_ONLY` 僅能代表審查清單內的研究或安全控制變更；不構成 Production、實單、排程或策略升版授權。

## Workflow 套用
- 每個 PR 使用既有 CI 加上獨立規則式安全證據產出與同 SHA 核對；兩者均不得被當成模型安全審查。
- 不要求 OpenAI API、Copilot 或其他付費模型 Secret。**免費預檢不得對外呼叫模型**，且需記錄 `AI_REVIEW_NOT_ENABLED_FREE_MODE`。
- 若 Repository Ruleset 還要求多名 reviewer，應由唯一維護者修改該規則；此文件本身不會改變 GitHub 平台分支保護。
- 自動修復僅能在白名單範圍建立 Draft PR；不得直接改 main、關閉安全 Gate、恢復停用 cron、執行付費行情或下單。
- 多視窗/多 PR 沒有新證據時避免重複工作；在實際 merge 前以最新 main 做衝突與差異檢查。

## 既有工作分流
- PR #522 已修改 `docs/SKY_VALIDATION_PROTOCOL_V1_0.md` 的單人治理敘述：不要重複修改同一處。
- PR #520/#518：適用自動修補 E2E 的特別 Gate。
- PR #511/#512：適用來源時間與真實盤中 Artifact 的特殊 Gate。
- PR #508/#515：適用成本/帳本與跨 Workflow API 去重 Gate。

## 上線驗收
提交本契約 PR 後，尚需最新 SHA 的 GitHub CI、規則式安全預檢 run/Artifact 讀回、Repository Ruleset 檢查與單人 W0/P0-G 可追溯決策，才能把免費治理範圍標記為 ENFORCED。真正 AI 模型審查維持 NOT_ENABLED，不得因文件合併宣稱全庫部署或 AI 已完成。
