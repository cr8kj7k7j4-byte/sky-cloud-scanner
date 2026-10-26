# W1｜Sky Swing 驗證實驗室 — Evidence Consolidation 2026-10-25

> Scope: Swing research / backtest / validation only. No Production promotion authority.
> Production baseline remains **Sky Swing V1.0**.
> Final W1 status may only be PROMOTE_CANDIDATE / HOLD / REJECT / ARCHIVE.

## 1. Governance boundary

- Production: Sky Swing V1.0 — ACTIVE.
- W1 may research, reproduce and validate only.
- Any PROMOTE_CANDIDATE may only be queued to W4 Shadow/Paper.
- No W1 result changes Production.
- Canonical sources: SKY_SYSTEM_REGISTRY_V2_1.md, RESEARCH_FREEZE_REGISTRY.md, SKY_VALIDATION_PROTOCOL_V1_0.md, SKY_MASTER_CONTROL_STATUS_20261025.md, Phase 3–7 contracts.

## 2. Swing Strategy Registry

| Item | Class | W1 Status | Notes |
|---|---|---|---|
| Sky Swing V1.0 | Production | ACTIVE | Formal 3–20D long-only baseline. |
| Swing transparent feature model 1–5D | Candidate / historical evidence | HOLD | Current-universe 100-symbol sample; 2026 previously observed. |
| Swing 3–20D robustness extension | Candidate / historical evidence | HOLD | Same current-universe artifact; not promotion-grade PIT universe. |
| Swing candidate stability extension | Candidate / historical evidence | HOLD | Same data limitations. |
| Market Regime × Net Expectancy evidence | Evidence-only | HOLD | 1,161-trade V1.8 comparison ledger; useful regime evidence, not a production rule. |
| Weak-Regime Mean-Reversion 5–20D | Rejected family | ARCHIVED | Frozen in RESEARCH_FREEZE_REGISTRY; no local retuning. |

## 3. Duplicate research found

Two workflows are operational duplicates:

- .github/workflows/validate-swing-3-20d.yml
- .github/workflows/validate-swing-3-20d-robustness.yml

Both download run 39963770301 historical artifact and execute:
`research/validate_swing_3_20d_robustness.py`
with the same output directory. They differ mainly in artifact naming. Do not count them as independent evidence.

## 4. Data Integrity audit

Historical artifact:
- Artifact: sky-history-5m-39963770301
- Expected symbols: 100
- Successful downloads: 100
- History files: 100
- 5m bars: 2,704,785
- File validation: PASS
- Observed range: approximately 2023-05-23 through 2026-10-22.

Critical Gate 0 issue:
`universe_manifest.json` explicitly states:
- deterministic sample from the **current** official TWSE/TPEx universe;
- survivorship warning: current listing universe is used to look backward and delisted names are absent.

Therefore:
- file completeness = PASS;
- promotion-grade Point-in-Time Universe / survivorship gate = **FAIL for this artifact**.

Additional unresolved Gate 0 items for this artifact:
- corporate-action adjustment not demonstrated;
- symbol-continuity audit not demonstrated;
- sector PIT mapping absent;
- benchmark PIT series for canonical Bull/Neutral/Bear definition absent;
- feature timestamp causality is structurally next-open after prior-day data in the validation code, but a full timestamp ledger is not persisted.

The system-level 2023+ PIT universe gate is PASS in the Registry, but this specific 100-symbol Swing artifact does not consume that canonical PIT universe. A promotion-grade rerun must use it.

## 5. Reproduction evidence — existing 3-factor 5D candidate

The existing robustness code freezes 5D Train IC weights using:
- trend_ma20
- trend_ma60
- market_breadth20

Reproduction on the historical artifact produced:
- research rows: 53,077
- Train (<=2024): 23,429
- Validation (2025): 17,611
- Test (2026): 12,037

Frozen full-train 5D feature weights:
- trend_ma20: -0.4006
- trend_ma60: -0.2107
- market_breadth20: -0.3887

Important interpretation: all three Train rank ICs are negative, so the selected top decile is contrarian / weak-state tilted rather than a conventional trend-following Swing candidate.

### 5D @ 0.45% round-trip cost

| Split | n | Expectancy | PF | Win Rate |
|---|---:|---:|---:|---:|
| Train | 2,344 | +0.2366% | 1.135 | 49.4% |
| Validation 2025 | 2,746 | +0.1724% | 1.073 | 50.5% |
| Test 2026 | 1,726 | +0.5225% | 1.244 | 48.8% |

### 5D @ 0.65% stress cost

| Split | n | Expectancy | PF |
|---|---:|---:|---:|
| Train | 2,344 | +0.0366% | 1.020 |
| Validation 2025 | 2,746 | **-0.0276%** | **0.989** |
| Test 2026 | 1,726 | +0.3225% | 1.144 |

Conclusion:
- 0.45% headline evidence is positive.
- 0.65% stress is not consistently positive.
- This candidate does not pass the required stress-cost stability gate.

## 6. Walk-forward reproduction — 5D candidate

At least 3 folds were checked by refitting on the then-available prior period and testing the next calendar year.

| Fold | Test year | 0.45% Exp | PF | 0.65% Exp | PF |
|---|---:|---:|---:|---:|---:|
| F1 | 2024 | **-0.2397%** | **0.880** | **-0.4397%** | **0.792** |
| F2 | 2025 | +0.1724% | 1.073 | **-0.0276%** | **0.989** |
| F3 | 2026 | +0.5059% | 1.216 | +0.3059% | 1.125 |

Fold-positive rate:
- 0.45% cost: 2 / 3 positive = 66.7%
- 0.65% stress: 1 / 3 positive = 33.3%

Therefore the 5D candidate does **not** show sufficiently stable after-cost edge across folds under stress.

## 7. Horizon evidence (exploratory only)

Using the same frozen 5D-derived score, longer holding horizons show stronger headline returns in 2025–2026, including 10D/15D/20D. However these are **not eligible to be promoted as a newly selected Champion** because:
1. horizon comparison is result-visible;
2. the score was frozen on 5D;
3. the universe is survivorship-biased;
4. 2026 is not fresh OOS;
5. portfolio-level overlapping-position simulation has not been completed on the canonical PIT universe.

Treat longer-horizon strength as hypothesis-generation only, not a promotion result.

## 8. Market Regime evidence

Existing evidence file:
`research/SKY_V2_1_MARKET_REGIME_NET_EXPECTANCY_20261024.md`

It reports 1,161 trades:
- baseline Net Expectancy +0.227R
- PF 1.678
- Win rate 42.5%

Fully weak state (weak_score=5):
- 4 half-year regimes
- 410 trades
- Net Expectancy -0.024R
- PF 0.945

Healthy state (weak_score=0):
- 3 half-year regimes
- 377 trades
- Net Expectancy +0.469R
- PF 2.740

Interpretation:
- Market environment materially affects Swing performance.
- Evidence supports retaining Market Regime as mandatory research/risk context.
- It does **not** yet validate a hard Bear kill-switch because the state sample is only 11 half-year periods and weak periods are not uniformly negative.

## 9. Concentration evidence from reproduced 5D selection

Single-symbol concentration is not excessive inside the 100-name research sample:
- Train top symbol share: ~3.63%; top-5 ~13.40%
- 2025 top symbol share: ~2.55%; top-5 ~12.27%
- 2026 top symbol share: ~3.07%; top-5 ~14.25%

However:
- this does not test industry concentration;
- it does not test canonical PIT universe breadth;
- it does not test capacity/liquidity under real position sizing;
- it does not replace portfolio-level overlapping-position validation.

## 10. Swing Evidence Matrix

| Gate / Question | Evidence | Status |
|---|---|---|
| Data file completeness | 100/100, 2.70M bars, validation_pass=true | PASS |
| Point-in-Time Universe on current Swing artifact | Current-universe backward sample | **FAIL** |
| Survivorship Bias | Explicit warning in manifest | **FAIL** |
| Look-ahead / entry causality | prior-day feature -> next-open entry in code | PARTIAL PASS |
| Corporate Action | no promotion-grade audit attached | BLOCKED |
| Symbol continuity | no promotion-grade audit attached | BLOCKED |
| Missing data | no missing/empty/parse errors in artifact | PASS |
| Train/Validation/Test separation | <=2024 / 2025 / 2026 | PASS structurally |
| Fresh OOS | 2026 previously observed | **FAIL / NOT FRESH** |
| Walk-forward >=3 folds | reproduced | PASS execution; stability FAIL |
| 0.45% cost | 5D positive in 2/3 WF folds | MIXED |
| 0.65% stress | positive in only 1/3 WF folds | **FAIL** |
| Bull/Neutral/Bear robustness | evidence exists but regime definitions/data differ across studies | HOLD |
| Exit comparison FIXED_3R / MA20_TRAIL / SWING10_TRAIL | no canonical current PIT replay completed in W1 evidence set | BLOCKED |
| Rule ablation | contracts exist; no complete canonical Swing remove-one matrix found | BLOCKED |
| Feature ablation | contracts exist; full canonical matrix not completed | BLOCKED |
| Portfolio concurrency / sizing / heat | not completed on canonical PIT Swing candidate | BLOCKED |
| Correlation / sector concentration | sector PIT map absent in artifact | BLOCKED |
| Single-symbol concentration | exploratory 100-name sample acceptable | PARTIAL PASS |
| Capacity / liquidity / turnover | no promotion-grade portfolio replay | BLOCKED |
| Shadow/Paper | not started / insufficient evidence | WAITING_FOR_FUTURE_DATA |

## 11. Core research questions — current answers

1. Does Sky Swing V1.0 have proven after-cost Edge?
   - **Not yet proven to promotion standard in this W1 evidence set.** Positive historical evidence exists, but canonical PIT + full portfolio validation is incomplete.

2. Which Rules truly improve Expectancy?
   - **Not yet proven.** Complete canonical Rule Ablation is missing.

3. Which Rules mainly lower DD?
   - **Not yet proven.**

4. Which Features lack stable value?
   - Existing 3-factor research shows weak/negative IC structure and unstable stress performance; no feature should be promoted or pruned from Production from this evidence alone.

5. Is Bear Market Gate genuinely beneficial?
   - Market-state evidence says regime matters, but a hard Bear gate is **not yet validated**.

6. Which Exit is most stable?
   - **BLOCKED** pending canonical PIT replay of FIXED_3R / MA20_TRAIL / SWING10_TRAIL and any still-active registry exits.

7. Portfolio-level positive expectancy?
   - **BLOCKED**.

8. Single stock / industry dependency?
   - Single-stock dependency not obvious in the 100-name exploratory sample; industry dependency **not tested**.

9. Acceptable under 0.65% cost?
   - Current 5D candidate: **No, not consistently**.

10. Ready for Shadow/Paper?
   - **No**. Gate 0 and portfolio validation are incomplete.

## 12. Champion / Challenger / Rejected

### Champion Candidate
None.

Do not result-select 10D/15D/20D from this visible experiment.

### Challenger List
- 5D 3-factor top-decile candidate — HOLD
- Market Regime risk gate candidate — HOLD / research context only
- Existing Production Swing V1.0 replay on canonical PIT universe — highest-priority validation work item, not a new strategy

### Rejected / Archived
- Weak-Regime Mean-Reversion 5–20D — ARCHIVE / no retune
- Any attempt to rescue current evidence by threshold/horizon tuning after seeing results — REJECT as governance violation

## 13. Outstanding Risks / Blockers

1. Current 100-symbol artifact is survivorship-biased.
2. Canonical 2023+ PIT universe exists system-wide but is not wired into the current Swing validation scripts.
3. 2026 is already observed; cannot be called fresh OOS.
4. Corporate actions and symbol continuity are not promotion-grade audited in the current Swing replay.
5. Exit comparison is incomplete under canonical PIT replay.
6. Rule/Feature ablation matrices are incomplete.
7. Portfolio overlap, max concurrent positions, 1R sizing, correlation, sector concentration, heat, capacity and turnover remain incomplete.
8. Shadow/Paper evidence must accumulate prospectively after research gates pass.

## 14. Final W1 Status

**HOLD**

Reason:
- Current evidence contains promising after-cost historical results, but
- promotion-grade Data Integrity fails on the available 100-symbol artifact,
- 5D walk-forward is mixed,
- 0.65% stress cost is not stable,
- portfolio/risk validation is incomplete,
- no fresh untouched OOS remains in the current historical window.

The next promotion-eligible experiment must be a pre-registered replay of Sky Swing V1.0 / frozen Challenger rules on the canonical 2023+ point-in-time universe, with fixed exits, 3+ folds, 0.45%/0.65% costs, rule/feature ablation, and portfolio validation. Only after those gates pass may W1 return PROMOTE_CANDIDATE for W4 Shadow/Paper.


---

## 15. Canonical PIT interface remediation — completed

W1 identified that the system-level 2023+ Historical Universe Gate was PASS, but the audit artifact originally persisted only summary evidence rather than the actual governed-window membership intervals required by downstream Swing replay.

This interface gap has now been remediated:

- `research/audit_historical_universe.py` now writes `pit_intervals.json`.
- Latest successful audit workflow run: **40193567617**.
- Persisted canonical intervals: **2,116**.
- Historical Universe Gate: **PASS**.
- Interval validation: **PASS**.
- Window unresolved events: **0**.
- The PIT snapshot contains the actual date-bounded membership intervals and can now be consumed by downstream research.

Governance consequence:

**PIT membership reconstruction is no longer the immediate W1 blocker. Historical price coverage for that PIT membership is now the blocker.**

## 16. Canonical PIT price-history readiness gate — completed

W1 added:

- `research/SKY_SWING_CANONICAL_PIT_REPLAY_PREREGISTRATION.md`
- `research/validate_swing_pit_readiness.py`
- `.github/workflows/w1-swing-pit-readiness.yml`

The pre-registration freezes the research question, universe, costs, exits, ablation requirements and portfolio validation before any canonical replay result is visible.

Latest readiness workflow:

- Run: **40193629353**
- Workflow conclusion: **success**
- Evidence status: **BLOCKED_PRICE_HISTORY_COVERAGE**
- Required minimum PIT price-history coverage: **95%**
- Available legacy historical price symbols: **100**

| Audit date | Canonical PIT symbols | Price-covered symbols | Coverage | Gate |
|---|---:|---:|---:|---|
| 2023-12-31 | 1,869 | 88 | 4.71% | BLOCKED |
| 2024-12-31 | 1,925 | 90 | 4.68% | BLOCKED |
| 2025-12-31 | 1,993 | 96 | 4.82% | BLOCKED |
| 2026-09-30 | 2,035 | 99 | 4.86% | BLOCKED |

Interpretation:

1. The legacy 100-symbol history is adequate for engineering regression / descriptive research only.
2. It is **not** adequate for promotion-grade Exit Comparison, Rule Ablation, Feature Ablation or Portfolio Validation.
3. Running those promotion gates on the legacy subset would reintroduce the exact survivorship / current-universe bias that the canonical PIT layer was created to prevent.
4. Therefore W1 deliberately stops those canonical tests at the data-readiness gate rather than producing misleading precision.

## 17. Existing non-canonical evidence retained as Evidence-only

The repository contains prior Swing-related evidence that remains useful for hypothesis and governance context but cannot substitute for canonical PIT replay.

### Ranking / portfolio evidence

`research/SKY_V2_1_ABLATION_RANKING_20261024.md`:
- 1,161-trade ledger.
- Opportunity ranking showed better historical Expectancy / PF / MDD than taking every qualified signal.
- Lower original stop distance was the strongest tested proxy factor.
- Top 3 was more year-to-year stable than Top 1.
- This evidence does not independently reconstruct fees/tax/slippage and is not canonical PIT replay.

### Anti-Chase evidence

`research/SKY_V2_1_ANTI_CHASE_PROXY_ABLATION_20261024.md`:
- 1,161 trades.
- Entry-vs-Trigger deviation did **not** show a stable standalone hard-gate benefit.
- Trigger-slip-only Anti-Chase is therefore rejected as a standalone hard gate.
- Composite Anti-Chase remains data-incomplete and requires contemporaneous VWAP / ATR / extension / resistance / liquidity / regime context.

### Generic ablation engines

- `research/feature_ablation_lab.py`
- `research/rule_ablation_lab.py`

These are valid research frameworks, but their existing datasets are not a canonical Sky Swing V1.0 PIT replay. Their existence means the ablation machinery does not need to be reinvented; the missing input dataset is the blocker.

### Legacy portfolio engines

- `research/analyze_portfolio_capacity_frontier.py`
- `research/audit_portfolio_decomposition.py`

These operate on the same legacy 100-symbol historical sample and fixed research weights. They remain descriptive evidence only and must not be counted as canonical portfolio-gate PASS.

## 18. W1 data handoff contract

The next valid canonical replay requires a 2023+ historical OHLCV dataset aligned to the persisted PIT intervals.

Minimum requirements:

- All symbols that are members of the canonical PIT universe during the governed window.
- Daily OHLCV is sufficient for the core 3–20D Swing replay unless an active rule explicitly requires intraday data.
- Adjusted / corporate-action-aware daily price series must be available and the adjustment flag persisted.
- Every row must retain symbol, exchange, trading date, open, high, low, close, volume and source timestamp / retrieval metadata.
- Missing ranges must be explicit; no forward-fill across non-trading or not-yet-listed periods.
- Price data must be joined only after membership eligibility is established for that date.
- Symbol continuity and market-transfer intervals must preserve the canonical interval identity.
- Coverage must be measured against PIT membership, not against today's listings.
- W1 readiness threshold remains **>=95%** on the registered audit dates; material missingness still requires fail-closed review.

Source engineering belongs to W3 / P0-DATA. W1 consumes the governed dataset and validates strategy evidence; W1 does not redefine Production data infrastructure.

## 19. Updated Swing Evidence Matrix

| Gate / Question | Latest evidence | Status |
|---|---|---|
| Canonical 2023+ PIT interval engine | 2,116 persisted intervals; audit run 40193567617 | **PASS** |
| PIT interval validation | valid=true; unresolved=0 | **PASS** |
| Canonical PIT price-history coverage | only 4.68%–4.86% using legacy 100-symbol history | **BLOCKED** |
| Survivorship-safe canonical Swing replay | cannot run until PIT price coverage is sufficient | **BLOCKED** |
| Corporate-action-safe replay | canonical adjusted historical price dataset not yet wired | **BLOCKED** |
| Train / Validation / OOS structure | contract frozen | READY; DATA BLOCKED |
| Fresh OOS | 2026 already observed | **WAITING_FOR_FUTURE_DATA** |
| Walk-forward >=3 folds | legacy execution exists; canonical replay blocked | LEGACY MIXED / CANONICAL BLOCKED |
| 0.45% cost | legacy evidence mixed-positive | EVIDENCE-ONLY |
| 0.65% stress | legacy 5D unstable | **FAIL on legacy evidence** |
| Bull / Neutral / Bear | regime effect supported; hard Bear veto unproven | HOLD |
| Exit comparison | preregistered; no canonical PIT replay dataset | **BLOCKED** |
| Rule ablation | framework exists; canonical PIT input missing | **BLOCKED** |
| Feature ablation | framework exists; canonical PIT input missing | **BLOCKED** |
| Portfolio validation | legacy engines exist; canonical PIT input missing | **BLOCKED** |
| Correlation / sector concentration | PIT sector / portfolio dataset incomplete | **BLOCKED** |
| Capacity / liquidity / turnover | canonical dataset incomplete | **BLOCKED** |
| Shadow / Paper | historical gates not complete | **WAITING_FOR_FUTURE_DATA** |

## 20. Updated core research answers

1. **Does Sky Swing V1.0 have proven after-cost Edge?**  
   No. Existing historical evidence is promising in places, but not promotion-grade because canonical PIT price coverage is only ~4.7%–4.9%.

2. **Which Rules truly improve Expectancy?**  
   Not yet proven under the canonical universe. Existing proxy evidence supports Opportunity Ranking as useful context, while Trigger-slip-only Anti-Chase is not a stable hard gate.

3. **Which Rules mainly lower DD?**  
   Not yet proven under canonical replay. Ranking / tighter candidate selection historically lowered MDD in the 1,161-trade ledger, but this is evidence-only.

4. **Which Features lack stable value?**  
   Signal freshness and Entry-vs-Trigger deviation are not stable standalone decision factors in existing evidence. No Production feature should be removed from W1 evidence alone.

5. **Does Bear Market Gate have true cross-period benefit?**  
   Market regime clearly matters; a hard Bear kill-switch is still unproven.

6. **Which Exit is most stable?**  
   BLOCKED pending canonical PIT historical prices and exact replay of FIXED_3R / MA20_TRAIL / SWING10_TRAIL.

7. **Is portfolio-level expectancy positive?**  
   Not proven to promotion standard. Legacy portfolio studies are survivorship-biased evidence only.

8. **Single-stock / sector dependency?**  
   Legacy 100-name single-symbol concentration was not excessive; canonical sector dependency remains untested.

9. **Is the strategy acceptable at 0.65% cost?**  
   Current legacy 5D evidence: **No, not consistently**.

10. **Ready for Shadow/Paper?**  
    **No.** Canonical PIT price-history coverage and downstream validation gates remain incomplete.

## 21. Final W1 status after executable-data exhaustion

**HOLD**

### Champion Candidate
None.

### Challenger List
- Frozen Sky Swing V1.0 canonical PIT replay — **BLOCKED by price-history coverage**.
- Existing 5D 3-factor research candidate — **HOLD / evidence-only**.
- Market Regime risk context — **HOLD / continue validation**.

### Rejected / Archived
- Weak-Regime Mean-Reversion 5–20D — **ARCHIVE / no retune**.
- Trigger-slip-only Anti-Chase as a standalone hard gate — **REJECT**.
- Any result-selected horizon / threshold / weight rescue after seeing legacy results — **REJECT**.

### Outstanding risks
1. Canonical PIT price history is materially incomplete (about 95 percentage points below the registered coverage gate).
2. Corporate-action-safe adjusted series is not yet connected to the canonical PIT replay.
3. Exact Production V1.0 exit/rule reconstruction has not been validated against the canonical dataset.
4. Sector PIT mapping / correlation inputs remain incomplete for portfolio concentration tests.
5. No future untouched OOS exists yet.
6. Shadow/Paper evidence has not begun because the historical validation funnel is not complete.

### Governance conclusion

All W1 work that can be completed **without pretending the 100-symbol current-universe history is canonical** has been completed or explicitly preserved as evidence-only.

The next dependency is a W3 / P0-DATA governed historical price dataset covering the canonical 2023+ PIT universe. Once that dataset is available, the frozen preregistration permits W1 to resume directly at canonical replay without asking for new strategy choices or retuning parameters.

Production remains **Sky Swing V1.0 ACTIVE and unchanged**.


## 22. Exact-rule reconstruction gate — 2026-10-26

Canonical PIT price-history readiness has now passed on the W3 repaired dataset:

| Audit date | PIT symbols | Price-covered | Coverage | Gate |
|---|---:|---:|---:|---|
| 2023-12-31 | 1,869 | 1,807 | 96.68% | PASS |
| 2024-12-31 | 1,925 | 1,863 | 96.78% | PASS |
| 2025-12-31 | 1,993 | 1,932 | 96.94% | PASS |
| 2026-09-30 | 2,034 | 1,970 | 96.85% | PASS |

Additional data evidence:
- symbol-day coverage: 95.83%
- price symbols available: 2,009
- duplicate rows: 0
- corporate-action conflicts: 0
- continuity conflicts: 0
- W3 repair workflow: PASS
- W3 → W1 repository dispatch: PASS
- W1 readiness: READY_FOR_CANONICAL_SWING_REPLAY

However W1 cannot yet execute a promotion-grade **Sky Swing V1.0** replay because the exact frozen Production rule specification is not reconstructable from the current SSOT.

Repository / history inspection found:
- Registry confirms Sky Swing V1.0 is ACTIVE.
- Existing 3-factor Swing scripts are research proxies / challengers, not an exact V1.0 implementation.
- PMS governs position-management safety but consumes externally supplied stop/target/add levels; it does not define the missing entry / setup / trigger / stop formulas.
- No canonical executable implementation for FIXED_3R / MA20_TRAIL / SWING10_TRAIL precedence was found.
- No complete Production Entry / Market Gate / Trend / RS / Setup / Trigger / Anti-Chase / RR rule definition was found.

Formal gate:
**BLOCKED_EXACT_RULE_SPEC**

Formal evidence:
`research/W1_SWING_V1_EXACT_RULE_RECONSTRUCTION_GATE_20261026.md`

Governance consequence:
- Data Gate = PASS.
- Exact-Rule Reconstruction Gate = BLOCKED.
- W1 final state remains **HOLD**.
- Production Sky Swing V1.0 remains ACTIVE / unchanged.
- Legacy 3-factor research must not be substituted for Production.
- No W4 handoff is authorized until exact-rule reproducibility is resolved.
