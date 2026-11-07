# Official forward disclosure snapshot pilot — 2026-11-08

## Verdict: HOLD / INCOMPLETE_DATA
- Source branch PR: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/322
- First Run https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42417305113: failed data-completeness gate; TWSE success, TPEx HTTP failure.
- Retried Run https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42417403829: 3 test cases passed, actual capture attempted, **artifact successfully uploaded even when source errors happened**, final completeness gate failed as designed.
- TWSE revenue: HTTP 200, 1,088 rows, raw bytes SHA256 `a58c04b3bdc2b94632027018ca4f09f6ad053848addb7b9580b372626542fc17`.
- TWSE material disclosures: HTTP 200, 5 rows at this retrieval, raw SHA256 `dc7e8ff888c5bdcb37096db725c9998ba626184193d00576dcb5be8336536b43`.
- TPEx revenue: HTTP **302**, no captured content, no sha; TPEx material: HTTP **302**, no captured content, no sha. Do not claim full TWSE+TPEx data chain operational.
- Older official **probe** Run #42416296354 returned TPEx HTTP 200 for current material disclosures and Run #42415830967 returned TPEx HTTP 200 for revenue, so this appears intermittent or requester-dependent; do not infer permanent TPEx outage or attempt to bypass access restrictions without checking official source behavior.
- HTTP 302 was not treated as a success or valid alternate source; debug HTTP behavior and any access policy first.
- The exact source bytes and manifest exist in the second run artifact (30-day provisional retention); GCS immutable durable archive **not configured or verified**.
- First observation timestamps are not issuer original publication timestamps, and latest monthly revenue aggregate cannot prove true historical PIT. Historical verifiable issuer-event count **0**.
- Paid Fugle API previous historical price-validation success remains independent and valid (PR #321); it cannot fix missing original filing timestamps.

## Best next steps
1. Confirm TPEx official OpenAPI redirects and status via approved data-provider access and repository runner, without abusive retries, and keep explicit diagnostics.
2. Obtain a suitable long-term storage target with retention, IAM/OIDC and object write-once policy; tests must prove persisted manifests and raw hashes before enabling cron. GitHub artifact retention is temporary.
3. Once snapshots can be durably saved, implement snapshot-to-snapshot change detections; still classify as `observed_at`, not `published_at`. For qualifying historical source, require independently verified original issuer times and amendment handling.
4. Run frozen Revenue MoM 5D, cost 0.45% / 0.65%, portfolio constraints, OOS/forward after Gate 0.
5. Keep PR research-only, **do not deploy, schedule, promote, or trade**.

This finding is a concrete infrastructure limitation, not a negative strategy-profitability backtest.