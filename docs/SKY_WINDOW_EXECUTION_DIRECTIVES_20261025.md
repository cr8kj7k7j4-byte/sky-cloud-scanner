# Sky Window Execution Directives — 2026-10-25

> Purpose: one operational handoff document for all active Sky windows.
> GitHub remains the Single Source of Truth. This document does not promote any trading rule.

## W0｜總控與版本治理
Execute continuously:
- ingest W1–W7 results;
- enforce Research Freeze Registry;
- maintain Champion / Challenger / HOLD / REJECT / ARCHIVE state;
- update System Registry and Master Control;
- prevent duplicate research and unauthorized Production changes.

Do not run bulk repetitive backtests.

## W1｜Swing 驗證
Status: HOLD.
Execute:
- prepare preregistered canonical-PIT Swing replay;
- define exact data dependencies;
- prepare fixed exit/rule/feature ablation plan;
- do not reuse the current-universe 100-symbol artifact as new promotion evidence.
No Production changes.

## W2｜當沖驗證
Status: HOLD / DATA_BLOCKED.
Execute:
- maintain compatibility between W3A dataset and PR #79 validation infrastructure;
- enforce fail-closed validation;
- once and only once the dataset passes, run 10-rule ablation + walk-forward + regime + 0.45/0.65 cost stress;
- report results to W0.
Do not promote or remove Production rules.

## W3A｜Data & Feature Engineering
Status: P0 / HIGHEST.
Execute immediately from:
- docs/W3_INTRADAY_PIT_REPLAY_DATASET_PRIORITY_20261025.md
- research/INTRADAY_PIT_REPLAY_CONTRACT_V1.md

Deliver:
- canonical historical decision replay dataset;
- builder/export pipeline;
- schema/version/lineage;
- PIT/leakage/coverage audit;
- manifest;
- direct validation with research/w2_intraday_validation_runner.py.

No Alpha changes.

## W3B｜Cloud & Production Engineering
Status: P1.
Execute:
- make W3A→W2 pipeline reproducible;
- GitHub Actions;
- Docker/runtime;
- artifact retention;
- logging/monitoring;
- retry/dedup;
- E2E;
- rollback rehearsal.
No Alpha changes.

## W4｜Shadow / Paper / Live Evidence
Status: WAITING_FOR_SUFFICIENCY.
Execute:
- continue canonical ledger accumulation;
- backfill outcomes where causally valid;
- track MFE/MAE/R/slippage/drift;
- publish sufficiency dashboard.

Minimum gate:
- >=200 samples
- >=20 trading days
- >=2 regimes
- >=95% outcome completeness
- <=20% single-symbol share

No Small Live before all required gates pass.

## W5｜Candidate Strategy Lab
Status: INTAKE ONLY.
Execute:
- screen new ideas;
- check Freeze Registry first;
- reject duplicate / low-value local retuning;
- only structurally distinct, PIT-feasible ideas may be queued to W0.
Do not create research volume for its own sake.

## W6｜Execution & Market Microstructure Lab
Status: P2.
Execute:
- spread/slippage/fill/liquidity/adverse-selection research;
- aggressive/passive execution;
- execution-adjusted RR;
- prioritize assumptions and historical fields usable by W3A/W2.
Unknown data stays UNKNOWN/BLOCKED.

## W7｜Global Trading Intelligence & Vendor Lab
Status: P4 / low intensity.
Execute:
- global methods / funds / papers / vendor / tools;
- evaluate independent information value and commercial value;
- route actionable candidates to W5, never directly to Production.

## Legacy W3
Status: DEPRECATED FOR NEW WORK.
Keep for historical reference only.
All new data/feature tasks go to W3A.
All new cloud/runtime tasks go to W3B.

## Current critical path
W3A → W2 → W4 → W0

Support:
W3B → W3A/W2
W6 → W3A/W2
W1 waits on reusable PIT path
W5/W7 remain controlled intake/research

## Autonomous execution rule
Within existing authorization, each window continues through its assigned scope without asking for step-by-step approval.

Stop and request user intervention only when:
1. a new external account/API credential is required;
2. real capital or irreversible risk is involved;
3. user-specific 1R/max-position must be set;
4. critical external data is unavailable;
5. a manual ChatGPT UI action is required.
