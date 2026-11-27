# Sky System Registry V2.1

> Canonical registry for production, research, rejected and evidence-only components.
> Engineering maturity labels do not imply profitability or future returns.

## W0 #363｜Fugle 方案 A 與歷史 5m 研究資料分層（2026-11-28）

本節適用全部 Sky 當沖／波段模型、全市場／單股／持股研究指令、手機報告、Workflow、CI 及研究 Artifact；**只統一資料證據語義，不變更 Production 模型版本**。

- **A1 全市場 Snapshot**：僅為 `OBSERVATION_ONLY` 初篩，保留 TWSE/TPEx 母體分母、資料日期、缺漏、覆蓋率。Snapshot `lastUpdated` 不能認證逐股成交時間。
- **A2 候選逐股 Individual Quote**：在同交易日以 `lastTrade.price/time`（或已證明合格的 `closePrice/closeTime` 成對備援）驗證實際成交及新鮮度。全市場 A2 覆蓋不足，不阻止 A1 研究觀察，但不得宣稱即時可買。
- **盤中 5m／Trades**：沿用 #775～#777 已存在的 opt-in、有界來源採證；完成棒須依 BAR_START/PIT 排除未完成棒。分頁有空頁終止且同來源 Quote/Trades/5m 數量一致，可標記研究級算術對帳；不可憑此宣稱原子 PIT、跨來源量單位或正式 VWAP 認證。
- **盤後／休市歷史 5m**：沿用 #802 的 `/historical/candles` 研究分流。Fugle 可能省略無成交時間；常規 5 分 K 起始點為 09:00–13:20，13:25–13:30 集合競價不產生常規棒，13:30 收盤撮合另成一根。**不設定任何最低 K 棒根數作為研究報告產生條件（包括 0 根）**。0 根時輸出 `OBSERVATION_ONLY_NO_5M_BARS`，繼續使用其他已認證來源輸出研究報告；K 棒衍生指標、K 棒量、K 棒訊號均標記無資料，不臆造數值。稀疏／無收盤棒需揭露實際涵蓋，不能自動認證完整性。時間戳、來源、交易日及資料合法性檢查仍保留。
- **成交量對帳**：整股分 K 的 `volume` 為張；日 K 的 `volume` 為股且包含不同交易別，**不可將分 K 加總直接與日 K 或交易所全日總量比較並宣稱相等**。交易所核對須先對齊交易別、截止時間與單位。
- **VWAP**：分 K `average` 是自開盤累積均價，不得當成每棒獨立 VWAP；逐筆成交加權均價可用於 `RESEARCH_ONLY`，缺乏原子 PIT/跨來源證據時 `independent_vwap_certified=false`。
- **共同指令／模型報告契約**：即使交易資格或研究策略規則 HOLD，仍可輸出帶日期、來源與缺漏的 `OBSERVATION_ONLY` 報告。只有完成行情、策略、成本後 RR、P0-R 才可給交易候選／張數。研究分數不等於勝率；不得藉報告接線提高 Production 版本、解除 `NO_TRADE` 或恢復自動下單。
- **付費及驗收**：不得重跑已有有效來源的 API；必要新增取數限於已核權限／速率／Claim 的 W0 最小證據路徑。工程 PASS、同次 Run/Artifact 讀回、跨來源資料 PASS、策略研究 PASS 與 Production 核准分開驗收。

官方資料契約：https://developer.fugle.tw/docs/data/http-api/historical/candles/ 與 https://developer.fugle.tw/docs/data/http-api/intraday/trades/；既有證據 #363 Run 45943803977 / 45944694345、PR #775～#777 / #802；固定根數缺陷由 #803 最小修復。

## Canonical architecture
P0-DATA → P0-K → P0-M → P0-EVT → P0-F → P0-AG → P0-S → P0-C → P0-O → P0-R → P0-X → P0-A → PMS → P0-L → P0-D → P0-G

Research namespaces:
- P0-ML: ML Research & Model Arena
- P0-LAB: Candidate Strategy Lab
- P0-PER: Personal Intelligence

## Production baselines

| Type | System / Model | Status | Notes |
|---|---|---|---|
| Production | Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP | ACTIVE | Current formal intraday baseline. No automatic promotion from research. |
| Production | Sky Swing V1.0 | ACTIVE | Current formal 3–20D long-only swing baseline. |

## Active research candidates

| Candidate | Status | Priority | Current evidence |
|---|---|---:|---|
| Swing 5D 3-factor top-decile challenger | HOLD | 3 | Existing 100-symbol artifact is current-universe backward and fails artifact-level PIT/survivorship promotion gate; 0.65% stress-cost stability is inconsistent; portfolio/risk and Shadow/Paper gates incomplete. Do not result-select longer horizons from observed data. |
| Revenue MoM 5D | PRE_PIT_CANDIDATE | 1 | Robustness gates passed, but 2023–2026 historical PIT audit found 0 / 87,588 company-months with verified MOPS filing timestamps (0.0000%). Promotion blocked until historical PIT coverage is resolved or the research window is redefined prospectively. |
| Revenue YoY 5D | HOLD_CONCENTRATION_FAIL | 4 | Primary/stress return gates passed, but top-5-symbol concentration exceeded threshold across splits. Do not promote. |
| Revenue YoY Acceleration 5D | PRE_PIT_CANDIDATE | 2 | Robustness gates passed, but 2023–2026 historical PIT coverage is 0.0000% (0 / 87,588 company-months). Remains pre-promotion research only; statutory-deadline proxies do not satisfy PIT. |
| Revenue YoY 20D | HOLD_CONCENTRATION_FAIL | 5 | Return gates passed, but concentration gate failed; do not promote despite high average returns. |

## Evidence-only features

| Evidence | Status | Use |
|---|---|---|
| vol20 market-residual relationship | FEATURE_ONLY | P0-F contextual feature; not a standalone long-only trigger. |
| drawdown20 residual evidence | FEATURE_ONLY | Research evidence only. |
| market breadth / relative strength | FEATURE_ONLY / CONTEXT | Market and ranking context; not standalone production alpha. |
| Top100 gainers universe | FEATURE_ONLY / CANDIDATE_POOL | Candidate-universe context only. Two independently preregistered Top100 Velocity selector variants failed after cost; Top100 membership alone is not a trade signal. |

## Rejected candidate families

| Candidate family | Status | Reason |
|---|---|---|
| P0-S 5m Breakout Candidate | REJECTED_OOS | Full 100-symbol validation passed; OOS n=9,111, PF=0.2033, Expectancy=-0.8018R at 0.45% round-trip cost. Do not promote to Paper Trading or live signal. |
| Weak-Regime Mean-Reversion 15D | REJECTED | Signal-level edge failed to survive ranking/capacity/broad-basket portfolio implementation. |
| Fixed-time intraday ranking | REJECTED | OOS and post-cost evidence insufficient. |
| Event-driven intraday ranking / catalyst stack | REJECTED | OOS and post-cost evidence insufficient. |
| Transparent intraday ML feature ensemble | REJECTED | Negative post-cost Train/Valid/Test performance. |
| Low-vol market-residual long-only | REJECTED_AS_STRATEGY | Stable IC did not convert into robust tradable long-only edge. |
| Stage 7A Broader Market Alpha | REJECTED | Pre-registered A1–A5 hypotheses failed stable-positive and cost gates; archived and no further local retuning allowed. |
| VNext Residual Ranking Baseline v1 | REJECTED | All preregistered 3D/5D/10D × Top3/5/10 variants had negative Validation and Research-Test expectancy after 0.45% cost with PF < 1; do not retune or escalate to nonlinear ML. |
| Top100 Velocity Baseline A family | REJECTED_STANDALONE / ARCHIVED_NO_RETUNE | Dual negative evidence: A1 Top3/60m n=9,934, 0.45% expectancy -0.4888%, PF 0.556; A2 top-decile/30m 9,949 signals / 8,685 entries, 0.45% expectancy -0.4285%, PF 0.528, 8/8 half-year folds negative. No local Top-N/time/lookback/weight/holding/stop-target rescue. Top100 universe remains FEATURE_ONLY context. |n=9,934; gross expectancy -0.0388%, gross PF 0.953; 0.45% expectancy -0.4888%, PF 0.556; all folds and 2023-2026 slices negative. Top100 universe retained as FEATURE_ONLY candidate-pool context. |

| Opening Retest Reclaim Baseline D | REJECTED_STANDALONE / ARCHIVED_NO_RETUNE | 2026-01-01–2026-10-22 whole-market 1m PIT; n=12,967; gross 60m expectancy +0.1032%, PF 1.312; 0.45% expectancy -0.3468%, PF 0.506; 0.65% expectancy -0.5468%, PF 0.372; open-stop rate 85.08%; H1/H2 both negative after cost. |

| False-Reclaim Short Baseline E (2026-10-26 preregistration) | REJECT_AFTER_COST_EXPECTANCY / ARCHIVED_NO_RETUNE | 2026-01-01–2026-10-22 PIT research; 60m short proxy n=10,732; gross expectancy +0.2241%, PF 1.792; 0.45% cost expectancy -0.2259%, PF 0.640; 0.65% cost expectancy -0.4259%, PF 0.458; H1/H2 both negative; original short eligibility/borrowability unresolved. Evidence: research/w2/SHORT_FALSE_RECLAIM_BASELINE_E_RESULT_20261104.md; Run 41752940845; Issue #220. Research-only; not Production. |

## Historical Universe / Survivorship audit

- Main-native live audit run: GitHub Actions #40177304792 (2026-10-25)
- Governed research window: 2023-01-01 onward
- Official sources healthy: 6 / 6
- Official events: 2,426
- Windowed intervals: 2,116
- Window unresolved events: 0
- Interval validation: PASS
- Historical source coverage: PASS
- Current interval coverage: TPEx 100.0000%; TWSE 99.9081%
- PIT membership: 2023-12-31 = 1,904; 2024-12-31 = 1,960; 2025-12-31 = 2,028; 2026-09-30 = 2,069
- Historical Universe Gate: **PASS for the governed 2023+ research window**
- Promotion-grade 2023+ research must use the point-in-time universe rather than today's listing universe.
- Full-history strict ledger still contains 231 pre-window unresolved events; do not describe this as complete all-history coverage.

## Historical Revenue PIT coverage audit

- Audit run: GitHub Actions #40168078271 (2026-10-25)
- Scope: TWSE + TPEx monthly revenue, 2023-01 through 2026-09
- Expected company-months: 87,588
- Verified MOPS filing timestamps: 0
- Historical PIT coverage: 0.0000%
- Gate: FAIL
- Governance consequence: Revenue candidates remain PRE_PIT_CANDIDATE.
- The MOPS latest-finance endpoint `t51sb10` supports latest records only; its more-info form exposed only `Stp` and `TK`, with no year/month/date history selector in the probed official interface.

## Promotion gate

A Research Candidate may become Production only after ALL of the following 18 gates pass:
1. Point-in-Time Data Alignment.
2. Leakage Check.
3. Survivorship Bias Check.
4. Pre-registration.
5. Train / Validation Separation.
6. OOS.
7. Walk-forward.
8. Market Regime Stability.
9. 0.45% primary round-trip cost test.
10. 0.65% stress round-trip cost test.
11. Portfolio Validation.
12. Concentration Validation.
13. Correlation Validation.
14. Capacity / Liquidity Validation.
15. Max Drawdown.
16. Shadow / Paper Trading.
17. P0-R Risk Gate.
18. P0-G Promotion Review.

Any material gate failure blocks Promotion. No chat window, notebook, branch, or researcher may override this by subjective confidence or local retuning.

## W0 governance authority

- W0｜Sky 總控與版本治理 is the only control workstream authorized to consolidate W1–W7 outcomes into formal Strategy Registry / Research Freeze / Champion-Challenger decisions.
- GitHub remains the Single Source of Truth; a chat-only conclusion is not a formal version change.
- W1/W2 may validate and report candidates but may not self-promote Production.
- Major governance changes must be written back to GitHub.
- W0 does not absorb bulk repetitive backtesting; that remains delegated to W1 / W2.

## V5.4 正式當沖與手機快掃（2026-11-26）

依 #363 決議，保留 A1 Snapshot 初篩、A2 逐股真實成交認證及原子 Claim。正式當沖和手機快掃停用即時五分 K／獨立逐筆 VWAP 請求和探針，且這兩項退出正式掃描工程驗收。既有歷史資料與離線研究保留。依賴停用資料的策略維持 HOLD／NO_TRADE，Snapshot、average 或 A2 均不得替代策略所需資料。正式掃描仍須同次 Artifact 及獨立讀回。

## Fugle monthly subscription vs operational duplicate control (2026-11-26)
<!-- FUGLE_MONTHLY_SUBSCRIPTION_POLICY_V1 -->

**使用者已確認 Fugle 為包月付費方案。** Sky 不得把每次必要的行情 API 查詢預設為「額外按次收費」，也不得僅為避免臆測的單次費用而拒絕已授權、符合速率與配額限制、具有資料認證必要性的候選逐股 A2 補查。包月價格與權限、速率、配額仍以帳戶實際方案及 Fugle 官方資訊為準；包月**不代表無限 API 呼叫**。

**付費 Claim 是跨 Workflow 的操作防重與競爭保護，不是按次計費開關。** 保留既有共享 concurrency、原子 Claim、nonce／Artifact 獨立驗證、同次快取及失敗時 fail-closed。若遭 DUPLICATE_BLOCKED，先核對 run ID、scope、時間窗與現存 Claim／原始回應，確認是否為真正重複工作；不得因包月就取消並發防重或在未知實際 entitlement 時無界重試。

允許在 Provider-First 確認官方 Endpoint、帳戶權限、rate limit／quota，以及同次 Claim／快取後，**有界、必要、不重複**地追加行情驗證。對缺少成交時間、來源、封棒、成交量單位、獨立 VWAP 或完整 Artifact 的標的繼續 HOLD／NO_TRADE。Workflow 在 Job 建立前即失敗、零 Job／零 Artifact 時，不能推定為 Fugle 計費或配額異常，應先查 YAML、觸發事件與 Actions 編譯／權限原始證據。

此條是正式治理語意校正，不代表本帳戶的即時方案權限已核准，也不等於已執行 Fugle API、CI 或真實盤中掃描。不得新增重複 Workflow、排程、模擬帳本、自動下單或 Production 升版。

## W0 REUSE_FIRST / FALLBACK_PROVIDER_FIRST / EVIDENCE_BEFORE_PASS (2026-11-24)
<!-- SKY_W0_REUSE_FIRST_FALLBACK_V1 -->

**適用範圍：** W0～W7、日內與波段 Production 基線及研究分支、Fugle/TWSE/TPEx、CI、Actions、Artifact、手機 E2E。唯一工程主線仍為 [#363](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/issues/363)；只有 W0 可寫 GitHub 工程程式、PR、Workflow 與驗收決策。既有研究與正常運作功能不得因本政策刪除或重寫。

1. **REUSE_FIRST / KEEP：** 每項工作先讀當時的 main SHA、#363、OPEN/MERGED PR、Workflow/CI、真實 Run/attempt/event/HEAD SHA、Logs、Artifact/Digest、既有研究註冊表與 Freeze Registry。若現有功能等效且證據完整，直接繼承，標記 KEEP 或 REJECT_DUPLICATE，不建立第二個實作、排程、付費探針或回測。
2. **FALLBACK_PROVIDER_FIRST：** 主要路線因 API 缺欄位、權限、資料時段、Rate Limit、缺歷史資料或服務不可用而受阻時，先保留原始錯誤與來源證據、查官方資料能力及本帳戶實際權限；未確定時標記 HOLD_PROVIDER_CONFIRMATION。優先評估**已授權的同供應商官方替代 Endpoint／模式及現有快取/Artifact**，其次才評估有來源契約與授權的其他供應商。替代方案若不能等價滿足原母體、PIT、成交、量、VWAP、風控及付費 Claim，必須維持 HOLD/NO_TRADE，不直接轉正。
3. **ONE_FIX_ONE_OWNER：** 只有有原始重現證據、可定位為 CLIENT_INTEGRATION_DEFECT 且未被既有 PR 修補的問題，才由 W0 使用一個問題編號與最小 PR 修改；其他狀態分類為 PROVIDER_UNSUPPORTED、ENTITLEMENT_OR_RATE_LIMIT、PROVIDER_DATA_OR_DOCUMENTATION_ISSUE、TRANSIENT_FAILURE 或 INSUFFICIENT_DATA，不捏造程式修復。
4. **EVIDENCE_BEFORE_PASS：** 修改後分別查 Exact-SHA CI、W0 單人可追溯自審、main 合併、新正式 Run、同次 Artifact 與獨立讀回。必須區分 push/schedule/issue_comment/workflow_dispatch；任何來源、封棒、成交量、VWAP、Claim 並發、手機結果鏈缺一步，維持 HOLD。策略前瞻正期望值及 Production 授權另審，不以 CI 或 fixture PASS 替代。
5. **ANTI_DUPLICATE / NO_TRADE：** 不重啟已封存策略或模擬帳本、不買資料方案、不增重複排程、不自動下單、不追高、不向下攤平、不放寬停損。未知真實持倉/日損/連續停損不得視為零；無合格標的就禁止新進場。
6. **FAST_PATH：** W0 優先盤後可驗證的缺口及同次證據鏈；W3A 查行情能力與 entitlement、W3B 查正式 Run/Artifact/手機、W6 查 5m/成交量/VWAP、W4 唯讀獨立驗收。每小時最多 20 個子輪次只是上限，無新缺口即停止；不得以輪數替代已完成工作或憑空聲稱持續背景修復。

**靜態 CI 範圍：** 既有 governance-e2e 的 W0 去重稽核可驗證核心檔案仍存在、正式 scan.yml 的費用/付費 Claim/來源 Gate 與本政策不被刪除。它**不能**替代 Fugle 即時授權、API 成交紀錄、真正並發唯一性、策略驗證或 Production 審查。

## Hard governance rules
- Research cannot bypass P0-C or P0-R.
- News and event evidence are not direct trade signals.
- No single Agent can create an executable trade.
- Missing evidence is UNKNOWN / VERIFY_BEFORE_TRADE.
- TRIGGERED does not mean automatic buy.
- Formal production baselines remain unchanged until promotion gates pass.

## Validation evidence state

- W1 Swing validation: **HOLD**; no promotion-grade Swing challenger is currently authorized.
- W4 Shadow/Paper: **WAITING_FOR_SUFFICIENCY**; minimum gate remains >=200 evaluable samples, >=20 trading days, >=2 regimes, >=95% outcome completeness, <=20% single-symbol share, plus portfolio/cost/capacity, P0-R and P0-G review.
- W5 Candidate Lab: no active VNext Alpha candidate is currently authorized.
- Production baseline remains unchanged until all 18 Promotion Gates pass.

## W2 intraday validation infrastructure — updated 2026-10-26

- PR #79 research infrastructure remains accepted by W0/P0-G.
- Accepted components: canonical Intraday PIT Replay Contract, fail-closed validator, 10-Rule ablation, walk-forward/regime stability, 0.45%/0.65% cost stress, W2 validation runner, CI tests.
- Sky Day Trading v1.4 / P0-C MVP remains the Production baseline and its behavior is unchanged.
- No Day Trading rule is newly promoted to Production Stable Rule.
- Corrected whole-universe 5m PIT market source now **PASS**.
- W0 governance decision: historical full-rule replay for Production v1.4 is **NOT FULLY RECONSTRUCTABLE from the current SSOT**.
- Formal W2 status: **HOLD / HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE**.
- W2 must not report historical 10-rule efficacy for v1.4 from reconstructed/proxy rules.
- W2 remains available for future challengers and any strategy whose frozen implementation + PIT evidence are complete.
- Canonical decision: `docs/W0_V14_HISTORICAL_REPLAY_GOVERNANCE_DECISION_20261026.md`.

## Workstream operating state — 2026-10-25

- W0: Master Control / P0-G — ACTIVE.
- W1: Swing Validation — HOLD.
- W2: Intraday Validation — **HOLD / HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE**; future challenger validation remains available.
- W3A: Data & Feature Engineering — canonical PIT / whole-universe market data source ready; maintain data provenance and do not synthesize missing v1.4 Alpha rules.
- W3B: Cloud & Production Engineering — ACTIVE / P1, supporting reproducible forward evidence pipeline and Production hardening.
- W4: Shadow/Paper/Live Evidence — **P0 HIGHEST PRIORITY / WAITING_FOR_SUFFICIENCY**; active forward evidence accumulation.
- W5: Candidate Strategy Lab — INTAKE ONLY.
- W6: Execution & Market Microstructure Lab — ACTIVE / P2, execution evidence only.
- W7: Global Trading Intelligence & Vendor Lab — ACTIVE / P4, low-intensity intelligence/vendor research.
- Legacy W3: DEPRECATED FOR NEW WORK.

Current critical path: **W4 → P0-R / W6 execution evidence → W0 / P0-G**.

## W3A historical intraday coverage status — updated 2026-10-26

- W3A replay engineering framework: **ENGINEERING COMPLETE**.
- Corrected whole-universe 5m PIT raw source: **PASS**.
- Source run: GitHub Actions #40221377923.
- Symbols with bars: 2,022 / 2,025 expected = **99.8519% symbol coverage**.
- Symbol-day coverage: **98.9071%**.
- Minimum daily coverage: **97.3726%**.
- Bars kept after corrected PIT membership filtering: **54,187,242**.
- Duplicate bars: 0; conflicting duplicates: 0; out-of-membership bars: 0.
- The old ~100-symbol artifact remains engineering-only historical evidence, but it is no longer the best available intraday source.
- Current v1.4 historical blocker is **missing authoritative frozen v1.4 rule provenance**, not market-data breadth.
- New preregistered challengers with frozen executable rules, including Top100 Velocity, may use the corrected whole-universe source for historical validation.

## W5 / W7 inbound queue — 2026-10-25

- PR #93 merged: `efae134bda8318bb018a251e0c679726e0af3e44`.
- ACCEPT_FOR_PREREGISTRATION: **0**.
- HOLD: **3**.
- Priority 1: Overnight-to-First-30m Reversal — HOLD / DATA_BLOCKED.
- Priority 2: Dynamic Futures/ETF/Spot Lead-Lag — HOLD / DATA_BLOCKED pending synchronized timestamp/session/roll causality.
- Priority 3: Broker-Identity / Skill-Conditioned Flow — HOLD / HARD DATA GATE / DO_NOT_BUY NOW.
- No Production change and no new formal Pre-registration authorization.

## Intraday PIT data acquisition policy — 2026-10-26

- Current bottleneck: promotion-grade whole-universe synchronized historical intraday coverage, not framework implementation.
- Acquisition sequence is fixed:
  1. Existing Fugle historical-minute capability / GitHub secret feasibility probe.
  2. If and only if that cannot reach the governed PIT gate, evaluate minimum official paid TWSE + TPEx historical intraday products.
  3. Paid purchase requires explicit user approval and does not itself satisfy validation gates.
- TWSE order-type history and Broker Flow data are not authorized purchases at this stage.
- W2, Overnight Reversal and Dynamic Lead-Lag remain HOLD while Gate 0 is unresolved.


## Realtime command routing — 2026-10-27

Canonical contract: `docs/SKY_REALTIME_COMMAND_CONTRACT_V1_0.md`.

- Current/update/scan/position/alert/full-analysis Sky commands are realtime-first.
- Whole-market scans use TWSE + TPEx official current universe plus TWSE MIS TSE + OTC operational quotes.
- Single-stock and position updates require the latest obtainable quote and timestamp before decision output.
- Unrecognized current-state Sky commands fail closed as `REALTIME_REQUIRED_UNROUTED`; they must not silently use stale web rankings.
- Historical backtest and validation commands remain PIT historical workflows.
- Realtime data connectivity does not change strategy promotion state, Alpha rules, stops, targets, or P0-R/P0-G governance.


## Mobile result presentation — 2026-10-27

- Canonical presentation contract: `docs/SKY_MOBILE_RESULT_TABLE_V1_0.md`.
- Current-state scan/update outputs prioritize the unified 10-column mobile decision table.
- Bull/bear scores are evidence-comparison scores, not statistical probability or win rate.
- Missing governed trigger/max-entry/stop values remain `—`; no presentation layer may synthesize executable levels.


## Update-command unified presentation — 2026-10-27

- 所有包含「更新」的 Sky 指令統一使用 `SKY_MOBILE_TABLE_V1_0`。
- 單檔更新、Swing 5D 更新、波段更新、快掃更新、持倉更新皆適用。
- 持倉特有損益欄位可追加於主表後，不得取代或改寫主表。

## Canonical postmarket zero-volume query contract — 2026-11-26 / W0 #363

**Global rule for data display, report, mobile readback, W3A/W3B/W4/W6 evidence and postmarket research**:
`VALID_QUERY_ZERO_REPORTED_VOLUME_NO_PRICE` means the provider returned a
traceable, date-certified Fugle TSE/OTC bulk Snapshot row for a stock,
`last_price = null`, and **explicit numeric** `reported_volume = 0`.
This is a **valid completed information query** (with zero reported volume),
**not** a verified price or actual-execution certification. The observation
does not prove a trading halt, no off-venue trade, or verified market status.
Data must identify the source date separately from the observation time.

Eligibility requires returned exchange Snapshot, verified provider response and
source date no later than observation date, a matching stock Snapshot row,
non-trial data and a genuinely numeric zero volume. Missing Snapshot row,
unknown/boolean volume, provider/date mismatch or unsupported source must
remain `HOLD_UNVERIFIED_POSTMARKET_QUERY`, **not valid**.

Keep three distinct denominators:
1. **Formal whole-market stock universe** (includes excluded research stocks);
2. Research-observed universe with explicit exclusion list;
3. Valid information queries within research scope = priced observations +
   validated provider-zero-volume/no-price observations.

**Never** convert zero-volume/no-price to valid observed price, last executed
trade, A2 fresh quote, VWAP, A+ trade candidate, buy quantity or trading
permission. Never shrink the formal stock-universe denominator to enhance
coverage. Preserve `OBSERVATION_ONLY`/`NO_TRADE`, P0-R, atomic Fugle paid
Claim, rate limits and genuine trade-time/volume provenance checks.

Canonical implementation: `research/sky_postmarket_observation.py`;
regressions: `tests/test_sky_postmarket_observation.py`. Intraday scanners
and Production models keep their stricter original gates. Change of trading
eligibility requires a separately reviewed W0/P0-G approval and authentic
executed-quote evidence; this policy alone is not such approval.

## W0 #363 amendment — full official-universe query checks in BOTH market sessions (2026-11-26)

**Scope:** all W0–W7 analyses, intraday and postmarket whole-market research
displays, mobile reports, paid-provider evidence and acceptance.  This section
supersedes the earlier postmarket-only scope where they conflict.

For **every officially listed TWSE/TPEx symbol**, the information layer must
attempt matching against the two existing bulk Fugle Snapshot responses.
Research/trading exclusions remain **listed and audited in the information
report**, but cannot reduce the formal stock denominator or be counted as
successful queries if no response actually exists. Exclusion still prevents
ranking/entry; a full-market QUERY is not trading authorization.

Valid source-date-matched provider row with an observed price:
`VALID_QUERY_WITH_OBSERVED_PRICE`. Returned non-trial Fugle symbol row with
explicit numeric zero reported volume and no observed price:
`VALID_QUERY_ZERO_REPORTED_VOLUME_NO_PRICE`. Both count as a completed
**information query**, but the latter does NOT count as observed price or
fresh/executed-trade certification. In intraday information mode, the source
date must equal the local observation trading date; in postmarket research,
date must be parseable, no later than the observation date, and retained
explicitly as a **provider source date**, not falsely described as execution
time.

Missing symbol response, unknown/bool volume, trial quote, invalid provider
response, future/mismatched source date, or other failure:
`HOLD_UNVERIFIED_INFORMATION_QUERY`. Never infer no trading/halt merely from
volume=0 without official confirmation. No request or coverage manipulation
to force PASS.

Canonical reusable classifier `research/sky_query_validity.py` is invoked
by `research/sky_full_universe_information.py` (intraday information)
and `research/sky_postmarket_observation.py` (postmarket). Preserve separate:
full official information-query coverage, research-scope query coverage,
observed-price coverage, and A2 independently verified fresh executions.
The existing paid Claim, cache, A1/A2 fail-close, 5m PIT, VWAP, P0-R,
`NO_TRADE` and Production promotion gates are unchanged.
Regression: `tests/test_sky_query_validity.py`, existing postmarket tests;
W3B exact-HEAD CI is mandatory. Do not duplicate Workflow/cron/provider calls.
