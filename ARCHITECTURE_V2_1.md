# Sky V2.1 Canonical Architecture

This file is the canonical namespace for the consolidated Sky architecture.

## Production path

P0-DATA → P0-K → P0-M → P0-EVT → P0-F → P0-AG → P0-S → P0-C → P0-O → P0-R → P0-X → P0-A → PMS → P0-L → P0-D → P0-G

## Canonical IDs

- P0-DATA: Data Governance & Quality
- P0-K: Knowledge & Evidence Engine
- P0-M: Market Intelligence Engine
- P0-EVT: Event & Catalyst Intelligence
- P0-F: Feature Store / Feature Engine
- P0-AG: Agent Orchestration
- P0-S: Strategy Builder
- P0-C: Decision Engine
- P0-O: Opportunity Ranking Engine
- P0-R: Risk & Portfolio Management
- P0-X: Execution Engine
- P0-A: Alert & Monitoring Engine
- PMS: Position Management System
- P0-L: Trade Ledger & Outcome Engine
- P0-ML: ML Research & Model Arena
- P0-D: Learning & Validation Engine
- P0-G: Governance & Registry
- P0-LAB: Candidate Strategy Lab
- P0-PER: Personal Intelligence

## Deprecated collisions

- P0-A must not mean Data Quality or Agent Orchestration.
- P0-M must not mean Model Registry.
- P0-O must not mean Outcome Engine.
- P0-E is retired as an ambiguous ID.
- P0-LAB is the strategy research sandbox; P0-L is ledger/outcome only.
- PMS is position management; P0-PER is personalization.

## Hard safety rules

- News is evidence, not a trade signal.
- No single Agent can create an executable trade.
- Research-only models and strategies cannot bypass P0-C or P0-R.
- TRIGGERED means pending confirmation, not automatic buy.
- Missing event data is UNKNOWN / VERIFY_BEFORE_TRADE, never SAFE.
- Production promotion requires OOS, walk-forward, cost/slippage, leakage and paper/shadow validation.
