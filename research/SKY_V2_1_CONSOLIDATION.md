# Sky V2.1 Consolidation Manifest

Base: latest main at branch creation.
Integration branch: integration/sky-v2.1-consolidation

## Imported into this branch

- PR #12: Feature Store, Model Arena, Registry/Readiness/Trade Logger core
- PR #8: Monitor Engine, State Store, Strategy Builder
- PR #10: Market Intelligence, Relative Strength, Event Risk, structured Evidence Ledger
- PR #3 selected research components: Outcome, Ranking, Training Dataset, Walk-forward
- Existing main retained: P0-K, Agent Orchestration, P0-R, ML foundation/training pipeline, research source registry

## Intentionally not bulk-merged

- Old Data Quality / Feature Contract variants that overlap newer P0-DATA/P0-F concepts
- Old main.py copies from parallel PRs
- Duplicate registry/logger implementations
- Any code that would make research models production-eligible

## Current integration behavior

- main.py now wires market intelligence, event risk, relative strength, research-only Strategy Builder, P0-R, P0-A monitor state, P0-K evidence, and P0-AG orchestration.
- Redis state persistence is supported through MONITOR_STATE_BACKEND=redis.
- Strategy Builder remains production_eligible=false.
- Event Risk remains UNKNOWN until real event connectors are supplied.

## Next gates

1. CI green
2. Review output/JSON compatibility
3. Validate Redis in cloud runtime
4. Historical replay
5. Shadow/Paper trading
6. Only then consider production promotion
