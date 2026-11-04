# 已封存研究 Workflow 入口清理（2026-11-05）

## 清理目的
將已由 `research/RESEARCH_FREEZE_REGISTRY.md` 正式標示 `ARCHIVED_NO_RETUNE`、不應再次啟動的歷史回測入口從 GitHub Actions 現行 Workflow 清單移除；**不刪除**研究程式、測試、結果、舊 Git commits、Actions 歷史或治理檔案。

## 本次清理的 Workflow（共九項）
- `.github/workflows/w2-baseline-d-false-start-reclaim.yml`
- `.github/workflows/w2-false-reclaim-short-baseline-e-backtest-recovery.yml`
- `.github/workflows/w2-top100-velocity-baseline.yml`
- `.github/workflows/w2-top100-velocity-baseline-a.yml`
- `.github/workflows/stage6b-catalyst-backtest.yml`
- `.github/workflows/stage6c-interaction-research.yml`
- `.github/workflows/stage6d-reaction-first.yml`
- `.github/workflows/stage7a-broader-market-alpha.yml`
- `.github/workflows/backtest-weak-regime-portfolio.yml`

## 治理與後續執行
- 上述家族不得重新以舊門檻微調、改名、重複回測恢復 Production。
- 不刪 `SKY_SYSTEM_REGISTRY_V2_1.md`、`research/RESEARCH_FREEZE_REGISTRY.md`、`docs/SKY_VALIDATION_PROTOCOL_V1_0.md` 與歷史失敗證據。
- 保留 Sky v1.4 Production、Sky Swing V1.0、前瞻 W4、P0-R、正式資料驗收與故障告警。
- 清理只代表停止提供這九項 GitHub Actions 工作入口，不代表已取得合法即時報價、策略正期望或治理升版。
- 其他 Workflow 不得僅依名稱老舊或測試曾失敗而誤刪，仍須確認是否被其他 Workflow、排程或證據追溯所依賴。

## 第二批：已拒絕 OOS 回測工作入口（另四項）

- `.github/workflows/backtest-event-driven-rank-oos.yml` — Event-driven Intraday Ranking / Catalyst Stack：`ARCHIVED_NO_RETUNE`
- `.github/workflows/backtest-event-stack-oos.yml` — Event-driven Intraday Ranking / Catalyst Stack：`ARCHIVED_NO_RETUNE`
- `.github/workflows/backtest-intraday-rank-oos.yml` — Fixed-time Intraday Ranking：`ARCHIVED_NO_RETUNE`
- `.github/workflows/backtest-catalyst-event-oos.yml` — Stage 6B / Event Catalyst OOS 相關封存策略；不再重跑原始無效假設

以上僅移除 GitHub Actions 工作入口，不更動研究與凍結證據。保留 `vnext-residual-ranking-governance.yml` 等防止舊策略重啟的治理測試，不以刪除封存入口放寬治理。

## 第三批：遺漏的凍結 D/E 入口（另兩項）

- `.github/workflows/w2-opening-retest-reclaim-baseline-d.yml` — Baseline D 已在 RESEARCH_FREEZE_REGISTRY 標為 ARCHIVED_NO_RETUNE。
- `.github/workflows/w3a-w2-false-reclaim-short-baseline-e.yml` — False-Reclaim Short Baseline E 已封存，不再重新下載或跑原始歷史研究；原始程式與結果保留。

本批只移除 GitHub Actions 的兩個過時入口。研究程式、凍結登錄、歷史證據與 Production 完整保留，且增加持續回歸測試。
