# W6 → W0 Handoff｜Execution & Market Microstructure — 2026-10-25

## Governance

- Workstream: W6｜Sky Execution & Market Microstructure Lab
- Production impact: NONE
- Production baseline: unchanged / frozen at Sky V2.1
- Central registry modification requested from W0/P0-G only.
- No directional alpha strategy was created.

## Verified existing infrastructure

FACT:
- `src/execution_engine.py` already provides Gross RR, Fee/Tax RR, Execution-adjusted RR and a fill-adjusted research heuristic.
- `src/execution_calibration_ledger.py` already supports observed fee/tax/slippage/spread calibration.
- `src/trade_logger.py` P0-L preserves bid/ask plus a generic execution object.
- W2 Intraday PIT replay contract already contains execution fields and `execution_adjustment_gate`.
- W4 contract already requires Fill Rate, Slippage, Missed Trades and execution latency evidence.
- Shadow outcome remains counterfactual and is not actual fill evidence.

## W6 artifacts added

1. `research/W6_EXECUTION_MICROSTRUCTURE_LAB_CHARTER_20261025.md`
2. `research/W6_L1_EXECUTION_EVIDENCE_CONTRACT_V1.md`
3. `research/w6_execution_baseline.py`

The baseline utilities calculate:
- fixed Sky time bucket;
- fixed price bucket;
- L1 spread bps;
- long entry / exit slippage bps;
- slippage in R;
- 1m / 3m / 5m adverse selection;
- fill rate / missed trade rate;
- fail-closed validation for non-fill rows.

## Current research state

| Priority | Topic | Current state | Reason |
|---|---|---|---|
| P1 | Spread + Slippage Baseline | HOLD | Forward observed L1/fill sample not yet sufficient |
| P2 | Aggressive vs Passive Entry | HOLD | Requires labeled P1 execution attempts |
| P3 | Pullback vs Breakout Chase | HOLD | Requires comparable execution arms and missed-trade accounting |
| P4 | Fill Probability | HOLD | Requires filled/missed/cancelled labels |
| P5 | Adverse Selection | HOLD | Requires actual/paper fill timestamps and +1/+3/+5m observations |
| P6 | Order Flow Imbalance | INSUFFICIENT_DATA | No verified historical tick/L2 sequencing evidence |
| P7 | Microprice / Book Pressure | INSUFFICIENT_DATA | Same L2 blocker |
| P8 | Execution Router | HOLD | Router must not be trained before upstream evidence is validated |

## Microstructure data decision

Canonical status for historical L2 / full order-book work:

`INSUFFICIENT_MICROSTRUCTURE_DATA`

W6 will not use OHLC/K bars to fabricate:
- queue position;
- trade aggressor side;
- cancellations/replenishment;
- full book pressure;
- microprice;
- historical order-book fillability.

## Highest-priority executable next path

1. Forward-collect decision-time L1 bid/ask and quote timestamp.
2. Preserve each execution attempt and its explicit fill status.
3. Join actual/paper fill price/timestamp without backfilling fictional fills.
4. Build P1 distributions by:
   - time bucket;
   - price bucket;
   - liquidity;
   - execution type.
5. Quantify spread/slippage in bps and R.
6. Only after adequate evidence, pre-register P2 aggressive/passive A/B comparisons.
7. Hand validated execution assumptions to W4 for Shadow/Paper confirmation.

## Promotion rule

A W6 result may at most become:
`EXECUTION_CANDIDATE`

It still requires W0/P0-G review plus W2/W4 validation as applicable.

## W0 requested decision

Register W6 as an execution research workstream if governance accepts the charter.
Do not change Production rules, stops, targets, alpha triggers or current Champion baselines.
