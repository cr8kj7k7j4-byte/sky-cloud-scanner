# Nova market-data intake — isolated research / NOT Production

## Ground truth 2026-11-07 (user local screenshots)
- Windows Python 3.12.10; taishin-sdk 1.0.2; fugle-marketdata 2.4.1 in isolated venv.
- SDK login, API authorization, REST stock client, and two basic quote lookups succeeded.
- Samples: TSE 2330 and OTC 8088, both **dated 2026-11-06 13:30 Asia/Taipei**, retrieved over weekend.
- No evidence yet for live quote timeliness, level-2 book, rate limits, entire TSE+OTC symbol universe, official market source, cloud execution entitlement, or tradable fills.

## Boundary and security
- This is a research-only, **read-only** local collector. No trading, no real account endpoints beyond SDK authentication.
- Never commit PFX, passwords, IDs, tokens, raw SDK objects, account metadata, or logs with secret values.
- Do not put PFX or trading credentials in GitHub Actions until vendor confirms cloud/CI and market-data redistribution permission; prefer managed secrets and segregated read-only account.
- Never infer raw volume unit; inspect vendor contract.
- The local helper at `tools/nova_quote_probe.py` does not run automatically. It writes only allowlisted quote fields; review market-data license before sharing outputs.
- Preserve current formal production v1.4 / Swing V1.0 and existing scan.yml; no promotion without W0/P0-G review.

## Validation gates
1. Isolated venv with `taishin-sdk==1.0.2`, `fugle-marketdata==2.4.1`; verify `pip check`.
2. Local offline unit tests of `normalize`: correct symbol, missing price, wrong symbol, unexpected reply; no credentials involved.
3. Next TWSE trading day: sample a pre-open, 09:05 / 09:15 / 09:30 / 09:50 / 10:15 and post-close response and verify timestamps, source status and historical-versus-real-time categorization.
4. Compare against official TWSE and TPEx instrument universes, report valid symbol count / denominator and failure breakdown; distinguish entitlement failures, missing quotes, quote staleness, market session, provider rate limits.
5. Benchmark throughput, retries, timeout, quota; confirm full licensed market snapshot endpoint and data entitlement before scaling. Test recoverability and mobile output using sanitized reports.
6. Only then propose integration behind feature flag `NOVA_MARKETDATA_ENABLED=0` (default OFF); fail closed if data age or quality insufficient. Keep normal Production provider until verified.
7. Assess after-cost expectancy independently; connectivity is not alpha. Use docs/SKY_VALIDATION_PROTOCOL_V1_0.md and frozen research registry.

## User-local command example
```powershell
& "$env:USERPROFILE\Desktop\nova-test-env\Scripts\python.exe" -m pip check
& "$env:USERPROFILE\Desktop\nova-test-env\Scripts\python.exe" tools/nova_quote_probe.py --symbols 2330 8088 --output nova_probe.json
```

Status: **INSUFFICIENT_DATA / HOLD**. No positive-return or Production readiness claim.
