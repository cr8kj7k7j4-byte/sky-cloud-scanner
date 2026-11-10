# Sky 真正 AI 模型安全審查：啟用與驗收（2026-11-11）

## 實作
- `.github/workflows/sky-single-owner-security-evidence.yml`：原有 pull_request 唯讀規則式預檢（不使用 LLM）。
- `.github/workflows/sky-ai-model-security-review.yml`：新增受信任 main 的 `workflow_run` 實際 AI 模型審查，僅接收上一層允許的 PR 成功事件。嚴禁 checkout PR head，GitHub Token 僅唯讀。
- `scripts/sky_ai_pr_review.py`：GitHub API 讀取最新同 SHA 的同庫 PR diff，限制大小與檔數、禁止疑似金鑰外送，使用 OpenAI Responses API `store=false`，模型預設 `gpt-6-luna`；輸出 `sky-ai-review-evidence.json`，包含模型回應 ID、SHA、Run、發現項目與 HOLD 狀態。
- 任何缺金鑰、差異過大、無法對上 PR 最新 SHA、API 失敗、模型結果非 PASS，均 **fail closed**。模型 PASS 也不等於 W0/P0-G 核准，無自動合併、無自動交易、無 Production 升版。

## 唯一使用者所需操作
在 GitHub Repo → Settings → Secrets and variables → Actions → New repository secret，建立名稱完全相同的 `SKY_OPENAI_REVIEW_API_KEY`。內容使用獨立的 OpenAI Platform API 專案金鑰，限制支出；**不要在 ChatGPT 或 PR 貼金鑰**。ChatGPT 訂閱與 API 額度為不同計費。沒有憑證時任何人工模擬不得說實際 AI 模型審查成功。

## 正式驗收 Gate
1. 先在研究 PR 安全審查 `workflow_run` 的 trust boundary、差異與限額，不因本 PR 的一般 CI 成功而直接併入 main。
2. 受控整合至 main 後，PR 需依序觀測原安全預檢成功、`Sky AI Model Security Review` 真正由 `workflow_run` 觸發、OpenAI 模型完成回答。
3. 核對主工作流程的 Run ID、PR 最新完整 head SHA、模型名稱/response ID、實際模型結果 JSON、Artifact 的 zip 下載、JSON 讀回與有效期。
4. 檢查故障路徑：Secret 未提供、上游預檢失敗、過期 SHA、疑似金鑰、超大 diff、模型拒答或 429/超時，一律 HOLD。
5. 在 GitHub Ruleset 中只將經驗證可成功且能覆蓋目標 PR 的檢查設定為 required；不要設定第二人 review 數，也不要讓單純規則預檢取代模型審查。注意 `workflow_run` 的 commit/status 對應目標可能與 PR SHA 不同，應先驗證其能否作為 PR Required Check；若不行須建立獨立的同 SHA Checks 橋接，不能假稱分支已強制執行。
6. W0/P0-G 唯一帳號根據上述證據記錄明確的 `OWNER_GOVERNANCE_DECISION`，方可批准研究級整合。

## 重要限制
此方案會把經截斷限制與敏感字串防護的 PR 程式差異交給 OpenAI API。使用前先確認程式碼資料分類與第三方處理政策。金鑰與模型費用均待確認；未設定則保持 HOLD。模型產出是輔助審查，不能保證找出全部弱點，也不能替代 CI、安全掃描與真人治理決策。

## 狀態
**IMPLEMENTED_IN_DRAFT_ONLY / AI_E2E_NOT_VERIFIED / NO_TRADE / NO_AUTOMERGE**。
