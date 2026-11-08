# Sky 系統完成標準｜2026-11-08

此文件是 **驗收門檻**，不是系統所有功能已正常運行的聲明。以 `SKY_SYSTEM_REGISTRY_V2_1.md` 與 `research/RESEARCH_FREEZE_REGISTRY.md` 為治理依據。

## 八關工程驗收（各關分別判斷）

| 關卡 | 驗收證據 | 本次驗收狀態 |
|---|---|---|
| 模型身分 | 六個實際部署模型 ID、SHA、凍結規則、入口、權重、版本對應 | INSUFFICIENT_DATA；不能將兩正式＋五研究模型冒稱六個部署模型 |
| 指令路由 | `src/sky_command_router.py` 靜態路由與單元測試 | 新增測試；需 PR CI 實跑 |
| 富果行情 | 真實 HTTP／端點／權限、成交時間、TWSE＋TPEx 覆蓋 | 部分歷史兩檔驗證；全市場即時尚待獨立驗收 |
| 風控規則 | 實際 runtime env、風險參數、停損連虧及成本執行閘門 call-site | 待檢查；不得僅修改預設值宣稱修復 |
| 訊號生命週期 | 真實模型來源 → immutable ID／版本／資料時間 → 去重 → Outcome | 合約檢查有測試；真實紀錄與持續入帳待驗 |
| 成本後比較 | 同一時間尺度的交易／不交易反事實、成交品質、0.45%／0.65% 壓力測試 | INSUFFICIENT_DATA；不得由研究漲跌推定成交獲利 |
| 手機 E2E | 真實 Cloud Run revision、服務權限、13欄、資料時間、NO TRADE | 待端到端實測 |
| 排程 | 台北時區、交易日、Actions logs、產物、通知及重試 | 尚待真實排程驗證；不新增重複 cron |

## 靜態總閘門

`python -m research.sky_acceptance_gate` 產生 `output/acceptance/sky_acceptance.json` 與 Markdown 摘要。

僅驗證 checkout 版本中的正式檔案、指令路由與可選的觀察紀錄合約；**不**連接付費即時 API、不宣稱雲端部署、不執行六模型回測、不改 Alpha、不發出委託。

以 `--signals path/to/signal-records.json` 提供真實觀察紀錄時才會檢查紀錄缺漏、衝突或研究冒稱成交；**沒有檔案時一定標示 NOT_PROVIDED**，不得算入帳完成。訊號缺少模型版本、來源、可得資料時間、穩定 ID 均拒收；相同 ID 不同內容拒收。

## 管理規則

1. **區分五種成功**：程式測試、資料取得、研究訊號與結果入帳、Cloud Run 實際部署、正式策略資格；不得互相推論。
2. 研究訊號可先上線為 `RESEARCH_ONLY`，但不得繞過 P0-R 或 W0/P0-G，也不得捏造觸發／停損／成交價格。
3. 正式交易仍依現有兩套 Production 基準；研究模型不能自升 Production。
4. 風控配置疑點：`EXEC_ENFORCE_GATE` 預設 0；`CAUTION_LOSS_STREAK` 預設 3，與連續兩筆停損停止進場的已確認治理規則不一致；需確認 env、call-site 與整體回歸測試後由 W0 審核正式變更。
5. 未經已核定的模型來源，不以 Ranking 假裝經批准的策略 Trigger/Stop/Target。
6. 已封存 `ARCHIVED_NO_RETUNE` 不得藉微調重啟。
7. 繼續沿用 Issue #331／#227／#318 的實際驗收；不另造平行研究治理，不另加 ChatGPT 排程。
8. **只有工作流在 main 上確實啟用並產出、驗證資料與手機端均通過，才能宣告工程完成。** 新 PR CI 通過本身不代表工作流定時或正式服務成功。
