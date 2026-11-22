# W0｜2026-11-16～2026-11-20 歷史證據回溯盤點（研究級）

- 審查日期（台灣）：2026-11-22
- 基準 main SHA：`2e417e9c54409235eba7243cf22568e55ac2a602` (#623)
- 範圍：當沖 Sky v1.4、波段 Swing V1.0；2026-11-16、17、18、19、20（Asia/Taipei）
- 結論：**INSUFFICIENT_DATA / HOLD**。已盤點既有執行證據；**尚未取得五日完整可認證歷史行情與事前決策訊號**，不得宣稱完成五日逐筆回測。
- 不新增模擬帳本、模擬委託/成交/損益、重播、任何自動下單或 Production 規則變更。

## 後續補證｜2026-11-22 10:16 TPE（保留原始調查結論）

**這一節是較原調查新增的後續資料，不回寫 11/16～11/20 的事前交易訊號。**

- GitHub [Actions run #44975178358](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44975178358)，`event=push`、`head_sha=0bebf486a827e69f62a1838aebb3e928e114c28f`、執行結論 `success`，建立於 2026-11-22 02:14:48 UTC（10:14:48 台北時間）。執行 job `sampled-history` 的下載、匯出完整性和五分鐘 K 棒結構驗證步驟均 `success`。
- 原始 job 日誌逐檔顯示 10 檔五分鐘棒，根數依序 `243, 250, 126, 260, 263, 269, 234, 124, 45, 80`，共 **1,894 根**；後續 `validate_history_export.py` 日誌顯示 `expected_symbols=10`、`successful_downloads=10`、`history_files=10`、`total_5m_bars=1894`、`validation_pass=true`，且沒有 failed downloads、missing files、unexpected files、empty files 或 parse errors。
- `research.audit_weekly_history_5m` 輸出 `STRUCTURE_PASS_NOT_STRATEGY_VERIFIED`；10 檔逐檔分類均為 `STRUCTURE_PASS_NOT_PIT_VERIFIED`。該驗證只是取樣檔案結構、交易時段和逐日觀察，**不是全市場完整性、當時模型事前訊號、官方 PIT 母體、實際成交或正期望策略認證**。
- 同次 Artifact **#14735556373**（`w0-history-nov16-20-sample-44975178358`）已由 GitHub 清單確認存在且未過期；上述數量是從**同次 Workflow job 原始日誌**獨立讀回，並非聲稱已逐位元解壓 ZIP 驗 hash。
- **去重決策：** 這 10 檔既有資料優先保存／沿用，**禁止**由 #626 的 `w0-history-nov2026-one-shot.yml` 再次發送相同範圍的付費歷史請求。保留本 PR 研究報告與原始提交；一次性下載 Workflow 應列 `REJECT_DUPLICATE` 候選，在 #363/W0 四關治理後才處置。
- 原下方「未取得」指的是**原調查所檢視的執行紀錄範圍內**未取得符合當日策略回溯條件的行情與事前訊號。新取得的 10 檔歷史資料可以支持樣本資料 QA，不能倒填 11/16～20 當時沒有保存的決策快照。五日績效、成本後期望值與完整研究級結論繼續 `INSUFFICIENT_DATA / HOLD`。

## 後續正式讀回｜2026-11-22 原始 ZIP 獨立驗收

> 此段為在初次研究報告及 10:16 初步補證**之後**取得的獨立驗收；前段「尚未解壓 ZIP」是當時真實查核狀態，不抹除或倒填為當時已驗證。完整執行紀錄見 [唯一總控 #363 驗收留言](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/issues/363#issuecomment-7075406149)。

- 已讀取原 [Actions run #44975178358](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44975178358) **同次 Artifact #14735556373** 的原始 ZIP，ZIP SHA-256 `c0b06825a8ab47def2464ee7e1364b533dfa1ef592a1c827458b9be10389ebf4`。
- ZIP 內 `weekly_5m_quality.json` SHA-256 `43c49bf94dcc788575e58247a89f0412344f2008e79e9af301c10e2decb8754d`；`download_summary.json` SHA-256 `f7946614c2d5eb74f9f91a143616acf95be3d8c41964233fe8c004db7693b75d`。
- 10 檔 `history/<symbol>_5.json` 的原始檔案 SHA-256 **10／10** 與原品質 JSON 中各檔對應值一致；逐檔根數與逐日統計 **10／10** 一致。五日合計依序 `364／374／381／388／387`，共 **1,894 根**，離線結構驗證 **0 個違規**。
- **合格範圍僅是取樣 ZIP 內容完整性、來源及時間資料的結構**，不是全上市上櫃 PIT、事前不可變交易訊號、實際成交、成本後績效或正期望認證；缺漏仍維持 `INSUFFICIENT_DATA／HOLD`。
- 此類既有研究樣本已擁有可追溯原始 Artifact，**不可再次向 Fugle 發送相同範圍的付費歷史請求**。最新 main 已以 #647／#648 沿用既有原子 claim 防護；本 PR 舊下載器與新一次性 Workflow 不可整包合併，應以 `REJECT_DUPLICATE` 處理，只保留獨有報告及非重複 QA。
- 原第⑥項「P0-R 真實券商資金、持倉與已實現損益接線」已由使用者從 #363 研究級工程結案條件取消；研究風險計算與資料不足時禁止交易的安全限制仍保留。

## 1. 可獨立核查的來源與方法

1. GitHub Actions REST `GET /repos/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs?created=YYYY-MM-DD..YYYY-MM-DD`，針對 UTC 日期 11/16～11/20 分別核對；GitHub created 時區為 UTC，**UTC 每日總量不可當成台灣交易日完整掃描數**，並非全 repository 所有 Artifact 的完整原始資料下載。
2. 11/16 UTC：18 runs，均為 `Sky 10-Minute Recovery Watchdog (Research Only)`；11/17 UTC：22，同類型；11/18 UTC：23，同類型。
3. 11/19 UTC：45 runs；除 watchdog / repair 外，新增多個 PR unit checks / acceptance tests，包含 `Sky Chat Bridge Unit Checks`，不代表真實市場訊號。
4. 11/20 UTC：226 runs；已查看全部 3 頁執行概覽。其中 `Sky Swing V1.1 Live Whole-Market Scan` runs #44672555601 / #44672546964 皆為 test job 成功、`sky_paid_reservation` 與 `live-scan` **skipped**，兩者無 Artifact，**不得視為成功行情掃描**。
5. 11/20 UTC 18:32:18 的手機橋接 run #44793701790：run conclusion failure，head SHA `d5507eff7797ac9d4289b996ea23746994cea95b`。其 Artifact #14657476938（`sky-chat-44793701790`）已下載並解析。擷取時間為 **2026-11-21 02:32 Asia/Taipei**，非 11/20 盤中，因此僅作資料品質診斷，**不是 11/20 的歷史訊號或收盤行情**。
6. 該 Artifact：`DATA_BLOCKED_SOURCE_FAILURE`；`FUGLE_PAID_SNAPSHOT`；universe=1986、observed_price_count=1942（97.78% 參考價格覆蓋率）、stage1_candidate_count=0、stage2_attempted_count=0、5m attempted API requests=0、samples=[]、正式交易資格 false；Stage1 排除 `NON_CURRENT_SNAPSHOT_DATE`=1955、`NO_FUGLE_SNAPSHOT`=31。這裡的 31 缺檔不應重新定義成創新板阻礙，需先核對母體與排除清單。
7. 請勿將 Artifact 中回傳的 1,942 筆「參考價格」誤報為同交易日「認證成交」或有效因果行情。
8. `docs/W0_V14_HISTORICAL_REPLAY_GOVERNANCE_DECISION_20261026.md` 已判定 `HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE`，不允許用事後近似規則假裝完整歷史 v1.4。
9. 驗證準則：`docs/SKY_VALIDATION_PROTOCOL_V1_0.md`、`research/RESEARCH_FREEZE_REGISTRY.md`、`SKY_SYSTEM_REGISTRY_V2_1.md`。

## 2. 五日資料完成狀態（每一日都不得以其他日期冒充）

| 台灣交易日 | 可核驗同日行情（含時間與來源） | 事前訊號及原始判斷 | 當時模型 SHA | 績效資格 |
|---|---|---|---|---|
| 11/16（一） | 未在已盤點執行中取得 | 未取得 | 未取得**交易訊號對應** SHA（僅有 watchdog `4b81de00...`） | INSUFFICIENT_DATA |
| 11/17（二） | 未在已盤點執行中取得 | 未取得 | 同上 | INSUFFICIENT_DATA |
| 11/18（三） | 未在已盤點執行中取得 | 未取得 | 同上 | INSUFFICIENT_DATA |
| 11/19（四） | 未在已盤點執行中取得 | 未取得；PR unit tests 不算 | PR test SHA 可核查，但不等於交易模型訊號 SHA | INSUFFICIENT_DATA |
| 11/20（五） | 非當次盤中；11/21 02:32 的 Artifact 不得挪用 | 未取得合法的 11/20 盤中事前訊號 | 手機橋接失敗 run `d5507eff...` 僅證明當次程式版本 | INSUFFICIENT_DATA |

**重要：**「未取得」代表本次可存取的來源尚不能建立證據，不代表全世界不存在該日行情。不得以 0 筆候選推算 0% 勝率。

## 3. 確認的工程缺口（可改善，非 alpha 證據）

- P0：掃描結果與市場資料應保留 `trade_date_tpe`、`captured_at_utc`、provider timestamp、timestamp semantic、來源、完整性與排除原因；分開盤中及盤後診斷。
- P0：每次事前決策需不可變更的 `run_id`、`head_sha`、config/rules SHA、universe、signal_generated_at、可交易與否、禁入原因；不得回填不存在的決策狀態。
- P0：工作流 summary 綠燈不得取代 scan job、實際行情、Artifact、同次 readback 的逐項成功證據；`skipped` 一律計成資料不充分。
- P1：Snapshot、五分鐘 K 棒與 VWAP 的交易日、交易時間及因果關係須逐層核證；缺失 fail closed。
- P1：P0-X 基本現股當沖成本 Profile `USER_CASH_DAYTRADE_20261022` 及滑價/價差完整性與 P0-R 風控一致性需另驗。
- P1：Swing V1.0 必須採用其自身凍結的日/週線與持有期規則；不拿當沖訊號充波段；Swing V1.1 test-only 綠燈不算真實跑盤。
- 已退役模擬帳本相關欄位若仍出現在歷史 Artifact，只能標示 legacy，不得重建或納入結案。

## 4. 事先登錄的未來對照研究（**未執行、未獲得績效結論**）

比較族群 A（當沖）：**完全凍結且來源可信的現行決策觀察** vs **新增可驗證的盤中資料品質／因果證據要求**。主要目的為防止假訊號與錯誤資料；不可宣稱能提高報酬。

比較族群 B（當沖、獨立新結構假設）：在**事前已確認的行情階段和 VWAP/成交量有效性**條件下，比較健康回測 P3／二次突破 P4 觸發與原始觀察基準。只有在確定符合新策略結構、凍結規則與資料來源後才能執行；**不可**重開封存的 P0-S breakout / Opening Retest Reclaim D 等同族調參。

比較族群 C（波段、獨立新假設）：採用事前凍結的日週線一致性、流動性、成本後 RR 與 3～20 日退出規則，與 Swing V1.0 的**事前已存紀錄**比較。缺基準決策就暫停對照；不以本週結果選最佳持有天數。

比較方法：固定 universe、訊號時點與資料契約；可取得時分 train/validation/OOS、走步驗證 >=3 folds、Regime、因果、分母、漏接訊號、交易成本（0.45% primary 與 0.65% stress；另列使用者校準成本）、成本後期望值、PF、MDD、MAE/MFE、容量、集中度；只在樣本充分時解讀結果。**2026/11/16～20 已觀察資料只能當探索與 QA，不得宣稱未碰觸的 OOS**。

升版最低門檻沿用現有 Governance：可評估 >=200、未來交易日 >=20、行情環境 >=2、完整率 >=95%、單一股票 <=20% 等，並經 W0/P0-G，研究不能自動升 Production。

## 5. 後續核驗與結案門檻

1. 使用既有富果訂閱與 GitHub 研究工具，查明 11/16～20 是否另有**真正保留、帶 timestamp 的歷史行情**可合法回補；保留來源與 API entitlement 證據，不能重建 11/16 當時未保存的訊號。
2. 對確有「事前留存」的每筆訊號以 `run_id + head_sha + decision_time + symbol + trigger` 綁定；無資料則標成不可回溯，不強制估分。
3. 研究級只產出 evidence manifest、QA 報告與未來假設登錄；不建立模擬帳本、不自動下單、不修改 Production。
4. 對五日完整行情、事前訊號、成本及成交因果逐項核對；任何缺漏保留 **INSUFFICIENT_DATA / HOLD**，不得宣稱完成績效或研究級結案。

## 6. 核心連結

- [手機橋接失敗但留存診斷 Artifact](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44793701790)
- [11/20 Swing V1.1 僅測試、實掃跳過](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44672555601)
- [11/20 Swing V1.1 僅測試、實掃跳過（第二筆）](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44672546964)
- [11/20 Shadow Dashboard](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44672574916)
