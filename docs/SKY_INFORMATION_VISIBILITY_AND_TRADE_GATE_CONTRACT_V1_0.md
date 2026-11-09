# Sky 資訊完整呈現與正式交易資格分離契約 V1.0
日期：2026-11-09（Asia/Taipei）
狀態：PROPOSED / W0 REVIEW REQUIRED。此檔為規格，**不是正式掃描器或手機部署已生效的證據**。

## 目標
使用者要求：即使最終交易結論為「🔴 禁止新進場／未驗證通過」，仍應盡可能揭露可稽核的**事實資訊與研究訊號**供自行判斷。風控僅限制交易資格，不得把未通過風控誤轉為資料隱藏或零候選的假象。
**資訊可見性 != 訊號有效性 != 買賣授權**。維持 P0-R fail-closed、NO_TRADE、不下單、不得繞過 P0-G Production 治理。

## 資料與輸出契約（掃描、六模型、手機及文字指令共同適用）
1. 全市場範圍依上市 TWSE、上櫃 TPEx 分別列出應掃、實際請求、有效、拒絕、延遲、最後成交時間、時間來源、涵蓋率及拒絕原因。不把舊日、歷史、MIS OTC 備援、新聞或 GitHub 快照稱為當前官方完整盤中報價。
2. **分層保留**：（A）有效即時報價（B）報價部分完整／延遲（C）僅歷史行情或研究資料（D）拒絕／來源失敗。候選股應包括：A+ 已觸發、A 待觸發、X 不合格、UNKNOWN 資料不足；可顯示排序與統計，但不得將 UNKNOWN 改為 A+ 或猜測分數。
3. 每檔保留可得欄位：代碼、名稱、交易所、現價與 quote_asof、方向、模型/版本、原始研究多/空分數（僅有證據時）、觸發與最高接受價、停損、兩目標、成本後 RR、類別、動作、理由、來源 URL／run_id、資料品質與時延。缺值為 null／待確認；研究分數不得稱校準漲跌機率。
4. 六模型逐項回報 model_id、version、implementation_entrypoint、weights_sha（若有）、trained_or_rule_based、last_run_at、inference_status、signals_count、model_error、evaluation_status；模型註冊 != 真推論 != 正式策略。
5. 本輪掃描失敗仍發布 **非交易資訊報告**（時間、錯誤、部分已驗證資料、覆蓋率、缺資料原因、曾發生的有效研究訊號），並保持 market_data_gate=DATA_BLOCKED、trading_allowed=false、action=禁止交易。不得為顯示資料放寬全市場 gate，也不得因 workflow exit code=1 遺失 artifact。
6. 不以「0 合格交易標的」推論「0 原始掃描筆數／0 研究候選」；請分開標示 total_universe / retrieved / valid_quotes / research_candidates / A_plus / A / X / blocked / trade_eligible_count。
7. 人工操作權仍在使用者；系統建議可顯示「禁止交易」，不能自動送出訂單。不得以此要求繞過停損、成本、成交權限、風控、未經驗證升版。

## 手機展示
- 首頁始終顯示最後一輪 run/time、真實 data_asof、各市場覆蓋率、資料狀態、錯誤、候選類別及「資料部分可觀察；禁止新進場」兩個獨立欄位。
- 「即時掃描紀錄」逐輪保留 scan run ID、計畫時刻與實際時刻、執行與資料品質、上市/上櫃覆蓋、A+/A/X/UNKNOWN、報告連結、錯誤；保護認證及存取權限。
- 「六模型研究訊號」即使未核准交易仍展示有來源的研究方向與結果，明示 RESEARCH_ONLY / 未訓練 / 未驗證。
- 「系統健康」列出 Fugle HTTP/權限、逐市場資料、最新 GitHub schedule 和 Cloud Run revision；無權限或不可讀就標示待確認，不冒充正常。
- 掃描失敗時若舊資料仍可讀，應顯著標記「歷史／非即時」和 asof；不可覆蓋或冒充新結果。

## 完整市場驗收與即刻可用性限制
- 正式盤中掃描以現有 main .github/workflows/scan.yml 的 09:00–13:30 五分鐘 cron 為入口；GitHub scheduler 為 best effort，手動與定時驗收分離。
- 需確認主分支確實使用付費 Fugle 批量資料、合法權限、TSE/OTC 分市場真實有效成交及個股 timestamp；新流程需 W3A 審核並提供 run、log、artifact、coverage 與 JSON。
- W3B 確認手機和掃描報告來源之間的經認證資料接口、實際 Cloud Run revision/image SHA、登入 E2E。只修改手機不等於掃描已成功。
- **本規格提交或 PR CI PASS 並不代表真實全市場即時掃描已完成、已發布手機或六模型全部可推論**。須檢查實際交易日 workflow_dispatch/schedule 與 artifact；不可捏造目前價格或通過率。
- 任何內容輸出均不改變正式策略治理、研究封存清單與 P0-R 預設保護；正式 Production 更動需 W0/P0-G 正式審查。

## 最低驗收測試
1. quote_scope 不足 -> 有可檢視原始/部分股票資料，market_data_gate=DATA_BLOCKED 且 trading_allowed=false。
2. 零 A+ 但有 A/X/UNKNOWN -> 頁面顯示有觀察筆數且沒有「全市場無股票」的誤解。
3. 過期行情 -> 明確 asof、STALE，不填「即時」。
4. 六模型部分未訓練 -> 顯示 placeholder、NULL 分數、0 verified inference，不影響其他研究紀錄展示。
5. 私有 artifacts 權限錯誤 -> 顯示 PRIVATE_ACCESS_BLOCKED，不揭露 token 或將舊紀錄當當日。
6. 最新掃描 exit 1 -> 掃描 run/debug/artifact 仍保留，無交易資格。
7. 真正 live full-market + 成本後風控驗收前 -> NO_TRADE，不自動下單。
