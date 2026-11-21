# B01 Sky — Permanent removal of simulated trading ledger (2026-11-21)

Status: OWNER DIRECTIVE / RESEARCH ONLY / NO ORDERS.

## Mandatory removal
Remove all **dedicated simulated-trading ledger** implementations and dependencies from every model, scanner, command, module, test, workflow, artifact schema, watchdog, CI and acceptance gate. This includes #508 PAPER_ONLY simulated order/fill/position/PnL event recording, replay and cost-PnL ledger. #508 simulated-ledger delivery is **not** a release prerequisite.

## Preserve
Fugle snapshots, completed 5-minute candles, market data provenance, signal observations, readback, risk constraints, transaction cost profiles, cost-adjusted RR, strategy validation and NO_TRADE safety controls. Do not remove independent research evidence ledgers, disclosure/event provenance, or actual broker records solely because their filenames contain 'ledger'. Never interpret removal as permission to place orders or promote Production.

## Required acceptance (not yet complete)
1. Inventory tracked source files, workflows, tests, CLI routes, docs and acceptance checks on latest main and active PR heads.
2. Delete dedicated paper-trading components; refactor imports and callers; ensure missing simulated ledger never blocks read-only scans.
3. Remove only dedicated workflows, schedules and secrets references; do not disable shared scanning/watchdog workflows.
4. Add a narrowly scoped CI regression gate that fails if dedicated paper-trading ledger paths, imports, commands, workflow triggers or acceptance requirements return. Avoid generic bans on the words paper, shadow, ledger, simulation or cost.
5. Run unit/integration CI and verify same-run GitHub Actions artifacts and mobile readback without paid Fugle calls when possible.
6. Confirm all active PRs/branches cannot reintroduce the removed subsystem without explicit owner change control.

No acceptance claim until exact SHA, passing CI, changed-file inventory and GitHub Actions evidence are recorded.
