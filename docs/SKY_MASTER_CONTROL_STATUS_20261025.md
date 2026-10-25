# Sky Master Control Status — 2026-10-25

> 這是目前 Sky 的總控狀態板。正式策略狀態仍以 /SKY_SYSTEM_REGISTRY_V2_1.md 與 /research/RESEARCH_FREEZE_REGISTRY.md 為準。

## A. Production
- Day Trading v1.4 / P0-C MVP — ACTIVE
- Swing V1.0 — ACTIVE
- Baseline — FROZEN at Sky V2.1

## B. Completed Governance
- Canonical architecture — DONE
- Strategy/System Registry — DONE
- Research Freeze Registry — DONE
- 2023+ PIT Universe Gate — PASS
- Validation funnel — DEFINED
- Multi-window operating model — DEFINED
- Shadow/Paper outcome contract — DEFINED

## C. Rejected / Archived
- P0-S 5m Breakout — REJECTED_OOS
- Fixed-time Intraday Ranking — REJECTED
- Event-driven Intraday Ranking / Catalyst Stack — REJECTED
- Transparent Intraday ML — REJECTED
- Weak-Regime Mean-Reversion — REJECTED
- Low-vol Market-residual Long-only — REJECTED_AS_STRATEGY
- Stage 7A Broader Market Alpha — REJECTED
- VNext Residual Ranking Baseline v1 — REJECTED

Action: 不再局部調參重開。

## D. Active / Blocked Research
1. Revenue MoM 5D — PRE_PIT_CANDIDATE — Blocked by historical filing timestamp coverage.
2. Revenue YoY Acceleration 5D — PRE_PIT_CANDIDATE — Same blocker.
3. Revenue YoY 5D — HOLD_CONCENTRATION_FAIL.
4. Revenue YoY 20D — HOLD_CONCENTRATION_FAIL.

## E. Highest-Priority Remaining Gates

### P1 — Swing Evidence Completion
- Consolidate existing Swing robustness/stability evidence.
- Confirm Walk-forward/OOS/cost/regime/portfolio gates against current canonical PIT universe.
- If all pass, queue for Shadow/Paper only; no direct live promotion.

### P2 — Shadow/Paper Evidence Accumulation
Sufficiency candidate gate:
- >=200 evaluable samples
- >=20 trading days
- >=2 regimes
- >=95% outcome completeness
- <=20% single-symbol share

### P3 — Intraday Research Discipline
- Do not reopen rejected intraday families by threshold tuning.
- Any new intraday candidate must have structural preregistration and distinct hypothesis/data/label/execution architecture.

### P4 — Data / Production Engineering
- Strict TPEx official intraday all-market chain
- Feature schema/versioning/DQ productionization
- Alert retry/dedup
- Mobile/Dashboard API
- Champion promotion/rollback rehearsal

## F. Current Strategic Decision

STOP adding broad new modules.

Priority order:
1. Evidence completion
2. Shadow/Paper accumulation
3. Portfolio/risk validation
4. Production hardening
5. Only then new alpha research

## G. Promotion Rule

No candidate becomes Production unless:
PIT + leakage/survivorship + preregistration + walk-forward + OOS + cost stress + portfolio/capacity + shadow/paper + P0-R + P0-G all pass.

## H. Definition of "Stable Profitability"

不定義為每日獲利或保證獲利。
定義為：
- after-cost positive expectancy across adequate samples;
- acceptable and controlled drawdown;
- robustness across time and regimes;
- implementation/live performance close enough to research expectation;
- automatic risk reduction when edge deteriorates.

## I. Next Human Decision Needed

目前沒有。既有授權範圍內可繼續依 Workstream 執行。
真正需要使用者介入的情況僅限：
- 需要新的外部帳號／憑證；
- 不可逆部署或資金風險；
- 需使用者指定可承受 1R／實盤資金；
- 研究資料來源本身無法取得。
