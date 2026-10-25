# W2｜Intraday Validation Blocker Decomposition — 2026-10-25

## Status

**W2 = HOLD / DATA_BLOCKED**

Production baseline remains:
- Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP
- Sky V2.1 Baseline

No Production rule is promoted, removed, or retuned by this document.

## Purpose

This document records the highest-priority remaining W2 blocker after:
- merged PR #79 (canonical PIT replay + 10-rule validation framework);
- merged PR #89 (W3A canonical intraday PIT replay assembly layer);
- validation of existing canonical Sector RS, VWAP-entry and Execution RR modules.

The objective is to prevent duplicate engineering work and prevent incomplete proxies from being treated as promotion-grade evidence.

## Existing canonical modules — do not rebuild

### Sector / Relative Strength
`src/sector_rs_replay.py`

Already supports:
- effective-dated sector mapping;
- contemporaneous sector return;
- sector RS vs market;
- stock RS vs sector;
- explicit missing mapping behavior.

Remaining blocker is historical source coverage, not the formula.

### VWAP / Entry Location
`src/vwap_entry_replay.py`

Already supports:
- decision-time VWAP;
- price-vs-VWAP;
- session position;
- RVOL;
- spread when genuinely available.

The module explicitly requires values frozen at decision time and must not use later bars, MFE/MAE or realized outcomes.

Remaining blocker is decision-time historical input coverage, not the formula.

### Execution-adjusted RR
`src/execution_engine.py`

Already supports:
- Gross RR;
- fee/tax-adjusted RR;
- execution-adjusted RR;
- fill-adjusted research heuristic;
- explicit missing execution assumptions.

Missing spread/slippage/liquidity/fill assumptions remain `EXECUTION_INPUT_REQUIRED` and may not be silently converted to zero.

## Reconstructible once raw PIT history exists

The following can be regenerated deterministically without inventing new strategy logic:

1. Market context
   - contemporaneous market return;
   - breadth;
   - volatility;
   - market regime derived only from information available by decision timestamp.

2. Sector RS
   - from effective-dated sector mapping + contemporaneous returns.

3. VWAP / Entry Location
   - from cumulative decision-time VWAP and session-to-time price/volume state.

4. Multi-timeframe / Phase / Trigger / Composite Anti-Chase
   - by replaying frozen Production v1.4 definitions using only bars available at or before the decision timestamp.

5. Outcomes
   - MFE / MAE / R / false-breakout / missed-entry / net_r_045 / net_r_065 only after feature freeze.

## Genuine evidence/source blockers

Promotion-grade W2 validation still requires:

### A. Effective-dated historical sector membership
Must include source evidence and valid effective intervals.

### B. Synchronized whole-universe intraday history
Must be sufficient to reconstruct the contemporaneous candidate pool for every decision timestamp.

### C. Historical candidate decision snapshots
Either:
- true historical all-candidate snapshots, or
- a deterministic all-candidate replay of frozen Production v1.4 logic.

Winner-only records are insufficient because they introduce selection/survivorship distortion.

### D. Empirical execution evidence
Where available:
- spread;
- slippage;
- liquidity;
- fill behavior.

Unavailable values must remain MISSING / UNKNOWN. They must not be imputed to zero.

### E. Post-freeze outcome join
Must support:
- `net_r_045`;
- `net_r_065`;
- MFE;
- MAE;
- R Multiple;
- false breakout;
- missed entry;
- outcome completeness >=95%.


## Source-feasibility update — 2026-10-25

Two blockers previously labeled as generic external-data requirements are now narrowed:

### Sector membership: RECONSTRUCTIBLE_FROM_OFFICIAL_ANNOUNCEMENTS
TWSE and TPEx publish official industry-category adjustment notices with effective dates and before/after categories. Therefore 2023+ effective-dated sector membership should be reconstructed from official dated notices plus a verified current/base classification snapshot.

This is a W3A data-engineering task, not a new strategy hypothesis and not a reason to buy a third-party dataset by default.

### Whole-universe 5m history: EXISTING_AUTHORIZED_SOURCE / SCALE_ENGINEERING_REQUIRED
The repository already contains:
- `research/download_intraday.py`;
- `.github/workflows/export-history-5m.yml`;
- a configured GitHub `FUGLE_API_KEY` secret proven by the existing 100-symbol export.

The current 100-symbol artifact is not promotion-grade because it covers only about 4.8%–5.3% of the governed PIT universe and uses current-universe backward sampling.

The next step is not a new data vendor by default. It is a PIT-universe, sharded, rate-limit-aware whole-universe export and merge pipeline with survivorship-safe symbol membership by date.

### Remaining potentially external evidence
Empirical historical microstructure evidence (spread/slippage/liquidity/fill) may still require a distinct source or may remain explicitly MISSING/UNKNOWN where unavailable. It must never be silently imputed to zero.


## Formal W2 start gate

W2 canonical 10-rule efficacy work may run only when the replay satisfies:

- PIT Universe coverage >=95%;
- Market Context coverage >=95%;
- Sector Mapping coverage >=95%;
- Sector RS / price context coverage >=95%;
- Core Phase / Anti-Chase coverage >=95%;
- Outcome completeness >=95%;
- cost completeness =100% for each tested scenario;
- leakage audit = PASS;
- timestamp causality violations =0;
- explicit OOS rows exist;
- full contemporaneous candidate pools are preserved for P0-O validation.

If any mandatory gate fails:

**DATA_BLOCKED**

No Full Model expectancy, Rule Contribution, Stable Rule, or promotion claim may be emitted.

## Immediate W2 execution after unblock

Once the canonical replay passes the gate, W2 must execute without retuning:

1. 10-rule Remove-One Ablation.
2. OOS-only efficacy.
3. Walk-forward stability with >=3 eligible folds.
4. Market-regime stability with >=2 sufficient regimes.
5. 0.45% primary cost.
6. 0.65% stress cost.
7. Ranking-decile separation.
8. Capacity / liquidity sensitivity.
9. Sector concentration.
10. Single-symbol concentration.

Rule output status:
- STABLE
- MIXED
- NEGATIVE
- INSUFFICIENT_DATA

Final W2 candidate status:
- PROMOTE_CANDIDATE
- HOLD
- REJECT
- ARCHIVE

PROMOTE_CANDIDATE is only a handoff to W0 / P0-G and never modifies Production directly.

## Freeze compliance

W2 will not reopen `ARCHIVED_NO_RETUNE` families through:
- threshold changes;
- Top-N changes;
- stop/target changes;
- indicator-period changes;
- feature-weight changes;
- nonlinear-model escalation.

Any reopen requires a documented structural change under the Research Freeze Registry.

## Current conclusion

No new structural edge can be honestly claimed from the remaining repository state yet.

The highest expected-value action is therefore **evidence completion**, specifically blockers A–E, not another indicator or another parameter search.

This status does not imply existing Production rules are invalid. It means individual causal contribution cannot yet be isolated at promotion-grade PIT / after-cost standards.
