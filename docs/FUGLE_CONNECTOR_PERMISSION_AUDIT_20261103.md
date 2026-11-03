# Fugle connector permission audit — 2026-11-03 (Asia/Taipei)

Status: **CONNECTOR_AVAILABLE / GITHUB_API_UNVERIFIED / PRODUCTION_UNCHANGED**.

## Evidence and scope
Observed in the user's connected Fugle-Stock app at ~08:20 Asia/Taipei:
- list_content_specs: 49 returned spec entries; 47 marked accessible=true, 2 false.
- Explicitly inaccessible: FCNT000117 (broker trade Gini), FCNT000158 (Taiheng indicator).
- get_realtime_quote succeeded for TWSE 2330 / 6695 and TPEx 5425; returns market metadata including day-trade and short-sale *eligibility flags*, not borrow inventory or a trading signal.
- At pre-open, quote fields had prior close/reference, zero volume and no trade serial. Do not present the reference as a live executed price.
- get_all_watchlists succeeded; get_price_alert_quota returned count=0, max=10 at the time of testing. This is a connector alert quota, NOT a GitHub scheduler.
- FCNT000002 historical 5-year prices, FCNT000003 margin, FCNT000105 broker ranking, FCNT000153 15-year prices were called but returned no inspectable payload in this connector session. **Actual datasets are not validated**.
- Connector permissions are independent of GitHub Actions' FUGLE_API_KEY permissions, plan, quota and endpoint behavior. Never claim GitHub API is upgraded based on connector results.

## Source integration matrix (no production change authorized by this audit)
| Consumer | Available connector feature | Required independent verification before live enable |
|---|---|---|
| Day Trading v1.4 | equity quote + ticker flags | exchange-local timestamp, last trade, freshness, latency, intraday minute bars, liquidity, API key/quota, fail-closed source provenance |
| Swing V1.0 | FCNT000002/153/154, 005, 006, 091–093 | nonempty payload, period coverage, PIT publication timestamps, adjusted prices, corporate actions, lookahead and survivorship checks |
| Margin-liquidation rebound research | FCNT000003 | dates, field definitions, financing maintenance-ratio availability (NOT proven by margin balances), sufficient history, independent signals and costs |
| Short research | quote canBelowFlatMarginShortSell / canBelowFlatSBLShortSell flags | actual borrow availability, regulatory eligibility, separate short strategy hypothesis, triggers, cost and execution validation |
| Sky candidate alerts | get_price_alert_quota / alert rule APIs | consent before creating rules, ten-rule capacity, alert delivery and duplicate detection, separate from GitHub Action scan |

## Fail-closed acceptance criteria
1. Connector: capability list accessible != payload valid. For each required spec, check nonempty records, schema, symbol, timestamps, exchange, period and staleness.
2. GitHub: independently run actual FUGLE_API_KEY endpoint smoke tests within GitHub Actions, redact secrets, check 401/403/429, provider plan/quota and real outputs.
3. Intraday: after TWSE/TPEx market opens, validate quote and 1m bars against dated official sources; don't map referencePrice to current last price.
4. Research: PIT / publication latency / universe coverage / cost-stress / walk-forward / Shadow-Paper gates remain mandatory.
5. Warning: no automatic order, no production promotion, no archived-strategy retune, no unverified scores, buy limits or stop levels.
6. Only after repeated scheduled successful Actions runs can schedule reliability be described as verified.

## Governance and follow-up
Canonical rules remain Sky Day Trading v1.4 and Sky Swing V1.0, subject to SKY_SYSTEM_REGISTRY_V2_1.md, research/RESEARCH_FREEZE_REGISTRY.md and docs/SKY_VALIDATION_PROTOCOL_V1_0.md. W0/P0-G must review every Production change. Treat this file as a capability evidence ledger, not an activated data pipeline.

Pending: inspect every scanner source adapter and workflow, test real GitHub secrets without disclosing them, implement explicit API adapter/schema checks, run GitHub dispatch and verify logs/artifacts and scheduled triggers. Mark all pending gates **UNVERIFIED**, not PASS.
