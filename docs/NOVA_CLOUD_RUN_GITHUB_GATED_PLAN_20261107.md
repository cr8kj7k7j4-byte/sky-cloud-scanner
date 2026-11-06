# Sky Nova Cloud Run Jobs + GitHub Actions — design gate (research only)

Status: **HOLD — CLOUD DEPLOYMENT NOT APPROVED**. No credentials submitted, no cloud job deployed, no production scanner altered.

## Verified evidence (local only)
2026-11-07 home Windows: taishin-sdk==1.0.2 + fugle-marketdata==2.4.1, Nova auth and TSE/OTC snapshot successful.
V2.1 current-company-master coverage: TSE 1060/1093 = 96.98%, OTC 892/897 = 99.44%; TSE close-reference day differs; OTC close day matches. Weekend snapshots do not verify intraday lag.
Known gap: Innovation Board / halted / incomplete close, and legal entitlement. Strategy expectancy unproven.

## Proposed cloud architecture
1. **Google Cloud Run Job** (research-only, invoker-restricted; no HTTP/public endpoint) executes read-only Nova snapshot collection. Container executes once and exits, no order functions. Start with dry-run mode not requiring credentials. Keep deployed container separate from Production.
2. **Google Secret Manager** stores the PFX as a secret *file mount*, and login ID / password / PFX password as separately ACL'd secrets, only after broker's written approval for cloud-hosted certificate/auth. Use a dedicated service account with only needed secret versions and output write access; never publish or commit secrets.
3. **Private GCS bucket** stores sanitized quality summaries only if brokerage/market-data terms allow derived outputs to be stored/transferred. Full raw quotes should remain private under explicit entitlement and retention policy; never put raw feeds into public GitHub artifacts.
4. **GitHub Actions** invokes approved Cloud Run Job through Workload Identity Federation (OIDC) with restricted repository/branch claims; NEVER store permanent GCP key or PFX in GitHub. Run completion, freshness and failure alerts flow back via metadata-only evidence.
5. **Mobile summary** offers counts, source timestamps, missing/invalid counts, explicit HOLD/READY validation statuses; no fabricated price or transaction signal. Telegram/phone notification only after credential-free fail/success tests and recipient authorization.

## Mandatory readiness checklist
- [ ] Broker explicitly confirms cloud execution (Linux / Cloud Run Job), certificate placement, user-specific authentication and quote-use rights.
- [ ] Broker confirms whether separate *market-data-only* credential exists; do not expose order-capable principal by default.
- [ ] Check whether exports / private GCS reports / mobile notifications of derived quote stats are permitted.
- [ ] GCP project selected, billing alert, Cloud Run / Artifact Registry / Secret Manager / GCS and IAM access verified.
- [ ] Container built with separately pinned packages, Linux support and dependencies; test *without* credentials first.
- [ ] Dedicated workload identity federation and least-privilege service account, secrets isolated; audit logging configured.
- [ ] Dry run with mock data; no authenticated provider calls until permissions granted.
- [ ] Authenticated one-shot run; 2 market snapshot counts, timestamps, coverage; no broker secrets in logs.
- [ ] Benchmarked retries, 429 response, token expiry, timeouts, concurrency and no duplicate invocations.
- [ ] Validate exactly five Asia/Taipei scan slots on actual trading days (09:05, 09:15, 09:30, 09:50, 10:15).
- [ ] End-to-end phone report, delivery confirmation and failure escalation test.
- [ ] Formal W0/P0-G review before turning on a feature flag or merging to Production.

## Policy decisions
No cloud deployment and no secret copy until broker authorization is explicit. Existing GitHub schedule is not proof of punctuality. Do not mutate production models. Research status is INSUFFICIENT_DATA. Successful market feed is not profitable trading.

## Broker question
“請確認我已開通的 Nova API 個人帳戶，能否在本人專用 Google Cloud Run（Linux、非公開、僅自行分析）執行 API 登入並以 Secret Manager 保管 PFX 憑證及密碼？能否保存私人 GCS 的彙總資料、從 GitHub Actions OIDC 觸發執行並將不含原始行情的品質報告推送到本人手機？是否有固定 IP/設備/IP 白名單、登入次數、快照速率、授權範圍及其他限制？請提供書面規範。” 
