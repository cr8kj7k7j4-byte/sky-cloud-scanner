# Sky P0-DATA MIS live quote recovery | 2026-11-06

Status: PR #295, not production. This is an engineering evidence handoff, NOT an accepted real-time whole-market feed.

## Confirmed blocker
- main scan run 42147456080: 1,983 universe, 113 verified current-session executed quotes (5.70%); TWSE 36/1,091 (3.30%), TPEx 77/892 (8.63%).
- Diagnostic probe: 120 MIS symbols returned, but most last-trade z fields were '-' despite reference/open/high/low fields. Response presence is NOT trade coverage.
- Fugle single-name trade quotes work, bulk market snapshots TSE and OTC return plan_restricted.
- Official TWSE STOCK_DAY_ALL and TPEx tpex_mainboard_quotes are daily/closing endpoints, not current executed-trade coverage.
- Sources: https://openapi.twse.com.tw/ and https://www.tpex.org.tw/openapi/ and https://www.twse.com.tw/zh/products/information/information.html

## Experimental adaptive recovery
- Preserve bounded retries for truly omitted symbols and z='-' records: small MIS requests sometimes recover genuine last traded prices from a blank large response.
- Only for universe >=400 and source chunks >8, probe up to eight missing executions. Switch following batches to size eight only if >=6 of eight yield genuine valid traded prices.
- If sample recovery fails, stay on large batches plus existing bounded 80-symbol recovery.
- Stop adaptive small batches after two minutes or three consecutive failed provider requests.
- Count initial_missing_response, initial_present_without_executed_price, adaptive_probe_valid, adaptive_small_batch_enabled, adaptive_disabled_reason.
- Do not invent prices, bypass execution freshness, expand permissions, substitute reference values, or relax quote gating.

## Required acceptance
1. Existing and new CI tests green.
2. Compare real-session before/after quote coverage per exchange, request counts, 429/403/timeouts, time to finish, actual executed-trade timestamps, freshness rejects.
3. Preserve market gate >=80% total and >=70% each exchange, and treat MIS OTC only as operational fallback.
4. If live data does not improve substantially, do not merge adaptive mode; if requests exceed provider limits, use a properly authorized quote source instead.
5. W0/P0-G approval, actual scheduled run validation after deployment; no automatic trading or strategy promotion.
6. Paper/Shadow observations or engineering improvements do not establish after-cost profitable trades.

Status: market coverage improvement NOT YET VERIFIED on real data.
