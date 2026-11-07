# Minerva Habits of Mind → Decision Gates (isolated prototype)

Status: **RESEARCH ONLY**. Not Production. No scheduling, live signals, or automatic orders.

## Source and interpretation
Minerva's four competencies are critical thinking, creative thinking, effective communication, and effective interaction.
Official overview: https://www.minerva.edu/four-year-curriculum/
This repository's 8 engineering adaptations are **not** official Minerva stock-trading rules.

## Eight transferable practices
1. Evidence quality: source, timestamp, coverage, contradictory data → hard gate.
2. Counterexample search: document strongest opposing argument → hard gate on review completion, not sentiment.
3. Cognitive-bias check: chasing, averaging down, outcome bias → anti-chase hard gate; further biases need structured evidence.
4. Decision tree: insufficient evidence → block; no trigger → wait; research gate passed → observe only.
5. Probabilistic cost-benefit: transaction-cost-adjusted reward/risk ≥ 1.5. Do not treat model scores as probability.
6. Systems mapping: market, sector, instrument and correlated holdings; implementation pending separate validation.
7. Hypothesis testing: pre-registration, untouched OOS, walk-forward, cost stress; no archived strategy retuning.
8. Clear communication and retrospective: show verified facts vs inference vs unknown; preserve decision log.

## Current implementation boundaries
`minerva_gate.py` implements only deterministic gates (1, 2 review-presence, 3 chase, 4, 5 threshold).
This prototype **cannot verify data truthfulness itself**; upstream validators must supply verified booleans.
It does not implement (6–8), full research governance, complete transaction cost calibration, portfolio limits, or execution.
A positive gate result is always `觀察 / A`, NEVER `買進 / A+`.

## Local test
`python -m unittest research.minerva.test_minerva_gate`

## Governance
- Do not merge into main or activate live scan without W0/P0-G review.
- Do not reopen ARCHIVED_NO_RETUNE strategies via new wrapper labels.
- Preserve separate Sky Production and TRIDENT research behavior.
- Next integration requires independent data contracts, negative-path tests, execution eligibility, and full post-cost validation.
