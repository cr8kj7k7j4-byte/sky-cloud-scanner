# Sky V2.1 Baseline Freeze — 2026-10-25

> 本文件為 Sky V2.1 正式基準凍結聲明。凍結代表版本治理基準，不代表獲利保證。

## 1. Canonical Production Baseline

- Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP — ACTIVE
- Sky Swing V1.0 — ACTIVE
- Canonical architecture：
  P0-DATA → P0-K → P0-M → P0-EVT → P0-F → P0-AG → P0-S → P0-C → P0-O → P0-R → P0-X → P0-A → PMS → P0-L → P0-D → P0-G
- Research namespaces：P0-ML / P0-LAB / P0-PER

Production baseline 不因單次研究、單一回測或任何聊天視窗中的臨時結論自動升版。

## 2. Freeze Rules

1. GitHub `SKY_SYSTEM_REGISTRY_V2_1.md` 為策略與模組狀態的 Single Source of Truth。
2. `research/RESEARCH_FREEZE_REGISTRY.md` 為已淘汰／禁止局部重調之研究家族的 Single Source of Truth。
3. 任一聊天視窗、新 Notebook、新 Branch 不得以局部調參重新啟動 ARCHIVED_NO_RETUNE 家族。
4. 新研究必須先 Pre-registration，再 Train / Validation / OOS / Walk-forward。
5. 任何 Candidate 未通過成本、容量、集中度、P0-R、Shadow/Paper 與 P0-G 前，不得覆蓋 Production。
6. 2026 已使用過的資料不得再宣稱為 fresh untouched OOS。
7. 多方／空方評分為證據分數，不得稱作真實勝率。
8. 研究結果須區分：可觀察事實、分析推論、尚待確認資訊。

## 3. Current Evidence State

### 已通過的重要基礎治理
- 2023+ Point-in-Time Universe Gate：PASS。
- Canonical P0-K / P0-C / P0-O / PMS / P0-L 已收斂。
- Shadow/Paper ledger schema 與 outcome backfill contract 已存在。
- 研究升版 Gate 已固定為 PIT → Leakage/Survivorship → Pre-registration → Walk-forward → OOS → Cost → Portfolio → Shadow/Paper → P0-R → P0-G。

### 已否決、不得因局部調參復活
- P0-S 5m Breakout：REJECTED_OOS（n=9,111；PF=0.2033；Expectancy=-0.8018R；0.45% round-trip cost）。
- Fixed-time Intraday Ranking。
- Event-driven Intraday Ranking / Catalyst Stack。
- Transparent Intraday ML Ensemble。
- Weak-Regime Mean-Reversion。
- Low-vol Market-residual Long-only。
- Stage 7A Broader Market Alpha。
- VNext Residual Ranking Baseline v1。

### 仍被阻塞
- Revenue MoM 5D、Revenue YoY Acceleration 5D：Historical verified MOPS filing timestamp coverage 0.0000%，維持 PRE_PIT_CANDIDATE。
- Revenue YoY 5D / 20D：concentration gate failed。
- 真實 Shadow/Paper 樣本仍須累積至 Sufficiency Gate。

## 4. Freeze Exit Criteria

只有當 Challenger 完成完整 Promotion Gate 並由 P0-G 留下 Champion/Challenger 決策紀錄時，才可解除本基準並產生下一版 Production Baseline。

## 5. Goal

Sky 的目標不是「每次預測正確」，而是建立：
- 扣除成本後具可重複正期望的策略；
- 可控制的最大回撤；
- 對市場 Regime 改變具監控能力；
- 當 Edge 衰退時能停止交易／降風險；
- 所有決策可追溯、可驗證、可回滾。
