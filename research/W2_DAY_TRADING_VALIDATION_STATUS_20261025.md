# W2｜Sky Day Trading Validation Status — 2026-10-25

> Workstream: W2｜Sky 當沖驗證實驗室  
> Production authority: NONE  
> Production Baseline: Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP  
> GitHub is the Single Source of Truth.

## 1. Executive Decision

**W2 Final Decision: HOLD**

Reason:

The repository now has a canonical 10-Rule Ablation / Stability framework and a
fail-closed intraday PIT replay contract, but the historical replay dataset
required to execute a Production-grade Full Model ablation is not yet complete.

No new Production promotion is authorized.

## 2. Day Trading Strategy Registry

| Family / Component | W2 Category | Status | Evidence / Reason |
|---|---|---|---|
| Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP | Production | ACTIVE | Formal Production baseline; unchanged |
| P0-S Contextual Breakout v1 | Candidate | DATA_BLOCKED | Structurally preregistered successor; mandatory PIT context coverage not yet available |
| Market Gate ablation | Hold | RESEARCH_MORE | Context evidence exists, but Production-grade intraday replay is incomplete |
| P0-O Opportunity Ranking | Hold | RESEARCH_MORE | Ranking proxy evidence exists; not yet validated on canonical intraday PIT replay |
| Execution-adjusted RR | Hold | ENGINE_READY_DATA_REQUIRED | P0-X engine exists; explicit historical execution context/cost calibration incomplete |
| Sector / Relative Strength | Blocked | DATA_BLOCKED | Effective-dated sector mapping + contemporaneous RS replay incomplete |
| VWAP / Entry Location | Blocked | DATA_BLOCKED | Replay module exists; canonical intraday decision-time historical dataset incomplete |
| Composite Anti-Chase | Blocked | DATA_BLOCKED | Standalone trigger-slip proxy rejected; composite structural fields not yet fully replayable |
| Multi-timeframe Confirmation | Blocked | DATA_BLOCKED | No canonical decision-time historical replay table with frozen MTF states |
| Phase Gate | Blocked | DATA_BLOCKED | Phase definition requires deterministic PIT replay and coverage audit |
| Full 10-Rule Ablation | Blocked | DATA_BLOCKED | Cannot honestly compute until W2 PIT contract passes |
| P0-S Naked 5m Breakout | Archived | ARCHIVED_NO_RETUNE | OOS n=9,111; PF 0.2033; Expectancy -0.8018R at 0.45% cost |
| Fixed-time Intraday Ranking | Archived | ARCHIVED_NO_RETUNE | Rejected by OOS/post-cost evidence |
| Event-driven Intraday Ranking / Catalyst Stack | Archived | ARCHIVED_NO_RETUNE | OOS/post-cost evidence insufficient |
| Transparent Intraday ML Ensemble | Archived | ARCHIVED_NO_RETUNE | Negative post-cost Train/Validation/Test |
| Stage 6B Catalyst Score | Archived | ARCHIVED_NO_RETUNE | Frozen by Research Freeze Registry |
| Stage 6C Event Interaction | Archived | ARCHIVED_NO_RETUNE | Frozen by Research Freeze Registry |
| Stage 6D Reaction-first Intraday | Archived | ARCHIVED_NO_RETUNE | Frozen by Research Freeze Registry |
| Stage 7A Broader Market Alpha A1–A5 | Archived | ARCHIVED_NO_RETUNE | Stable-positive/cost gates failed |
| VNext Residual Ranking Baseline v1 | Archived | ARCHIVED_NO_RETUNE | All preregistered variants negative after 0.45% cost |

## 3. Stable Rules

**No Day Trading Rule is newly classified STABLE in this W2 cycle.**

Reason:
A STABLE classification now requires:

- canonical PIT replay contract PASS;
- >=3 eligible walk-forward folds;
- >=2 sufficient market regimes;
- positive direction consistency >=67%;
- 0.45% and 0.65% cost direction consistency;
- no leakage / survivorship / timestamp failure.

The historical decision replay table is not yet complete enough to satisfy those conditions.

This does not mean existing Production rules are invalid. It means W2 has not yet
produced sufficient remove-one evidence to claim individual causal value.

## 4. Mixed Rules

Current research-level / non-promotion evidence:

- Market Gate — plausible contextual/risk value, but intraday independent contribution not isolated.
- Opportunity Ranking — proxy evidence suggests relative selection value, but available evidence is not canonical intraday PIT ablation.
- Execution-adjusted RR — correct infrastructure direction, but historical execution assumptions are incomplete.

These remain **HOLD / RESEARCH_MORE**.

## 5. Negative Rules / Evidence

### Standalone Trigger-Slip Anti-Chase Proxy

Rejected as a standalone hard veto.

Interpretation:
Entry-vs-trigger deviation alone must not be promoted as the canonical Anti-Chase rule.

Composite Anti-Chase remains a separate structural hypothesis and is DATA_BLOCKED.

### Naked 5m Breakout Family

Negative evidence is strong and already frozen:

- OOS n = 9,111
- PF = 0.2033
- Expectancy = -0.8018R at 0.45% round-trip cost
- Expectancy remains negative at zero cost

Decision:
**ARCHIVE / NO RETUNE**

## 6. Rejected / Archived Families

Research Freeze Registry remains authoritative.

W2 will not rescue an archived family through:

- threshold tuning
- Top N tuning
- stop / target tuning
- indicator-period tuning
- feature-weight tuning
- nonlinear ML escalation after deterministic failure

Re-open is allowed only after documented structural change:

- new target
- new label
- new horizon
- new dataset architecture
- new execution architecture
- new market-neutral / residual framework
- new point-in-time evidence

## 7. Potential Structural Candidates

Allowed for future W2 study only after PIT/Data gates pass:

1. Contextual Breakout v1
   - Market Regime
   - Sector RS
   - Phase / Composite Anti-Chase
   - Frozen original breakout mechanics

2. Canonical 10-Rule Production Baseline Ablation
   - This is rule validation, not a new strategy family.

3. Execution-adjusted RR validation
   - Requires explicit cost model and empirical execution assumptions.

4. P0-O Ranking decile validation
   - Requires complete contemporaneous candidate pools.

No new broad indicator family is proposed.

## 8. Outstanding Data Gaps

Highest priority:

1. Canonical intraday decision replay table at:
   `symbol × observation_timestamp × candidate decision`.

2. Point-in-time Market State:
   - index return
   - breadth
   - volatility
   - contemporaneous regime

3. Effective-dated Sector Membership:
   - symbol
   - sector
   - effective_from
   - effective_to
   - official source evidence

4. Sector RS:
   - contemporaneous stock return
   - sector return
   - market return

5. Multi-timeframe states frozen at decision time.

6. Phase / Composite Anti-Chase:
   - cumulative VWAP
   - VWAP slope
   - ATR
   - extension ATR
   - RVOL
   - session position
   - stop distance
   - spread where available

7. Ranking candidate pool preservation:
   - complete pool
   - rank score
   - position
   - decile

8. Execution:
   - expected/actual slippage
   - spread
   - liquidity penalty
   - fill status/probability
   - cost model version

9. Outcome:
   - net_r_045
   - net_r_065
   - MFE / MAE
   - R Multiple
   - false breakout
   - missed entry
   - outcome completeness >=95%

## 9. New W2 Research Infrastructure Added

This W2 cycle adds:

- `research/INTRADAY_PIT_REPLAY_CONTRACT_V1.md`
- `research/intraday_replay_validator.py`
- `research/intraday_rule_ablation.py`
- `research/intraday_rule_stability.py`
- `research/w2_intraday_validation_runner.py`
- `tests/test_w2_intraday_validation.py`
- `.github/workflows/test-w2-intraday-validation.yml`

Phase 6 and Phase 7 contracts are expanded to the canonical 10-Rule set.

## 10. Completion Output

### Day Trading Strategy Registry
Completed above.

### Stable Rules
None newly proven.

### Mixed Rules
- Market Gate
- Opportunity Ranking
- Execution-adjusted RR

### Negative Rules
- Standalone trigger-slip Anti-Chase proxy

### Rejected Families
Governed by Research Freeze Registry; no retuning.

### Potential Structural Candidates
- Contextual Breakout v1 after PIT unblock
- Canonical 10-Rule baseline ablation after PIT unblock
- Execution-adjusted RR validation
- Intraday ranking decile validation

### Outstanding Data Gaps
Listed in Section 8.

## 11. W2 Final Governance Status

**HOLD**

Not:
- PROMOTE_CANDIDATE
- REJECT entire Production baseline
- ARCHIVE Production baseline

Reason:
Research infrastructure is ready, but mandatory historical PIT decision evidence
is not yet sufficient to isolate the contribution of all 10 rules.

Result is ready for W0 review. W0/P0-G retains sole Production promotion authority.
