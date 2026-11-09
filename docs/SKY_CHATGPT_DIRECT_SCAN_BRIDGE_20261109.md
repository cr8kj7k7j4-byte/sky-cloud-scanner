# ChatGPT Scheme A — Sky on-demand all-market bridge (2026-11-09)

## Status
**IMPLEMENTATION PREPARATION ONLY / NOT DEPLOYED / NOT CHATGPT-CONNECTED.**
Branch: `feature/chatgpt-sky-mcp-bridge-20261109`. No changes to production scanner, governance or trading rules.

## Verified baseline
- GitHub connector has read/write permissions.
- `src/sky_command_router.py` routes `Sky 當沖現在掃一次` to `src.main`; a route definition does **not** call a remote tool.
- `.github/workflows/scan.yml` has `workflow_dispatch`, but is a GitHub job, not ChatGPT direct Fugle API.
- `src/config.py` defaults `SKY_FUGLE_ONLY_MARKETDATA=1`. End-to-end enforcement and whole-market paid entitlement still require tests.
- `docs/SKY_REALTIME_COMMAND_CONTRACT_V1_0.md` and README retain references to older MIS quote paths. Audit active code before any production migration.

## Plan / gated deployment
1. Confirm ChatGPT workspace is entitled to install a **custom MCP with an action tool**. As of 2026-11-09 OpenAI help states full MCP write actions require Business or Enterprise/Edu. The currently observed Plus account cannot be assumed to support this. Do not claim installed.
2. Verify Fugle bulk endpoint, credentials, quotas and complete TWSE/TPEx coverage in the intended cloud runtime, with times and market breakdowns. Do not expose `FUGLE_API_KEY` to ChatGPT or logs.
3. Implement the durable authenticated HTTPS service `POST /api/sky/scans`, `GET /api/sky/scans/{scan_id}`, `GET /api/sky/scans/{scan_id}/results` backed by a persistent job queue/storage, deduplication and per-user rate limits. A transient Cloud Run instance's filesystem is NOT a durable queue.
4. Provide an authenticated Streamable HTTP MCP `/mcp` with `sky_start_scan`, `sky_scan_status`, `sky_get_results`. Scan start is an external write/action, must be permission-checked; it must NOT be connected to trading orders.
5. Use new server-generated `scan_id` per request, UTC start/finish, source and market-data timestamp, symbol universe counts, verified executed-trade coverage for TWSE/TPEx, scan job status, error reason, no stale fallback. 13-column observations use `src/sky_mcp_contract.py` validation.
6. Test auth rejection, duplicate requests, repeated scans, stale result IDs, partial market failure, off-market observation semantics, malformed 13-col rows, data source assertions, 95%+ scope if such a threshold is explicitly governed, and insufficient-coverage fail closed. New snapshots do not imply new intraday trades outside market hours.
7. Before deployment: tests, isolated staging, actual Fugle API cloud checks, tool discovery and test invoke from eligible ChatGPT account, authenticated request/response, complete artifact and status. Record links. Production requires separate approval and no research promotion.

## Current blocker
The ChatGPT MCP installation permission cannot be changed via a GitHub code change. The GitHub connector offers repository edits but no verified one-call full-market scan operation in this session. Do not claim that a GitHub push, report, or this branch has enabled live ChatGPT scanning.

## Output contract
- Full 13 columns defined by `src/sky_mcp_contract.py`; missing indicators stay null/待確認.
- Include `scan_id`, `data_timestamp`, `source=FUGLE`, `universe_count`, `verified_quote_count`, `coverage_pct`, `production_eligible`, `block_reason`, `run_url`, `automatic_order=false`.
- Report research observations even if blocked. Gate Production and candidate observations separately.
