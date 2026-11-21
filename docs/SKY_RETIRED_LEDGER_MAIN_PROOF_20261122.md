# B01 Sky — Retired simulated-ledger main-branch evidence (2026-11-22)

**Scope:** read-only inventory of `main` at `ecc5752919d5b66cce7ed27f49240ae50702e9aa`. Research only. This record does **not** assert deletion of Git history or every legacy branch.

## Verified evidence

- GitHub recursive tree of `main` returned `truncated=false`, **908 tracked blobs**.
- All **17 exact retired dedicated paths** in `research/sky_retired_paper_ledger_guard.py` / `RETIRED_PATHS` are absent from the `main` tree, including `src/paper_trading.py`, `research/sky_paper_only_acceptance.py`, `research/sky_paper_trade_trace.py`, the retired shadow modules, their tests and retired workflows.
- The guard itself, its regression tests and `.github/workflows/sky-retired-paper-ledger-guard.yml` intentionally remain as protective controls; they are **not** the retired simulated ledger.
- [Retired-ledger guard run 44921944163](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44921944163): successful pull-request CI. It is evidence of the guard working on that PR SHA, **not a fresh independent guard run on the latest main SHA**.
- [Latest mobile research scan run 44922128272](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44922128272): success on the above `main` SHA; weekend research-only report and same-run Artifact readback. It does **not** certify trading-session 5m data or VWAP.
- GitHub branches API was paginated through pages 1–8 (100 per page), returning **629 branch names**; some legacy branch names contain `paper` / `shadow`. Their trees and content were **not** exhaustively inspected, and no branches were deleted.

## Acceptance decision

| Gate | Finding |
| --- | --- |
| Known dedicated simulated-ledger files absent from latest `main` | **PASS — path inventory** |
| Narrowly scoped regression guard present | **PASS — source inspected; previous PR CI successful** |
| Full `main` source-token / import / CLI / workflow dependency scan independently re-executed at latest SHA | **NOT VERIFIED** |
| All 629 historical branch contents free of retired subsystem | **NOT VERIFIED** |
| Permanent deletion of historical Git objects | **NOT REQUESTED / NOT CLAIMED** |
| Live trading-session 5m and independent VWAP provenance | **PENDING** |
| Production eligibility or automated order placement | **PROHIBITED** |

## Follow-up without paid API calls

1. Execute `python -m research.sky_retired_paper_ledger_guard` in a clean checkout of latest `main`, capture exact SHA and machine-readable JSON result, and link its passing GitHub Actions run.
2. Verify any historical branch proposed for merging against the same retired-path/import/route guard. Do not merge old shadow/paper branches without review.
3. Continue the pre-existing 2026-11-23 trading-session acceptance check; do not classify weekend snapshots as certified 5m/VWAP.

No retired subsystem was reintroduced; no paid Fugle requests, broker orders or simulated-ledger operations are part of this evidence record.
