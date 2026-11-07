# Sky GCS research evidence — governance handoff (2026-11-08)

## Ground truth
- Real run [42425505869](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42425505869) on main: unit/store SUCCESS; four TWSE/TPEx feeds, create-only GCS raw readback, cross-day ledger. Source batches=2, provisional unique=2,271, unmodified repeat=2,271, revisions=0. This is **NOT** 2 independent trade days / 2,271 valid trades.
- Cross-day create-only ledger: `disclosure-forward-ledgers/v1/run-42425505869-attempt-1/ledger.json`, SHA256 `cb074c354622abcb785b5d015a1b55af44e0e7e8200587058f165c0d9ea69945`.
- Manual post-upload audit [42423986552](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42423986552): 5 verified objects. **`bucket_metadata_access=NO_PERMISSION_OR_UNAVAILABLE`**, no retention/IAM proof. Do **not** grant broad `storage.admin` to the writer to turn this green.

## Outstanding platform-admin evidence (human Console check)
Project `project-4f906c69-fa2b-456f-bab`, bucket `sky-disclosure-evidence-20261108`:
1. Cloud Storage > Buckets > bucket > **Protection**: record effective object retention, retention lock state, soft-delete period, versioning, and any lifecycle rules. Note that soft-delete 7d is *not* the same as locked retention.
2. Bucket > **Permissions**: check exact members and inherited IAM; public access prevention, uniform access and whether writer account `sky-disclosure-evidence-writer@project-4f906c69-fa2b-456f-bab.iam.gserviceaccount.com` has `storage.objects.delete` or `storage.objects.update`. Object User usually can delete/update; application create-only precondition alone is NOT WORM policy.
3. Workload Identity provider `sky-github-evidence/github-actions`: main-only, `workflow_dispatch`-only condition is deliberate. Changing it to allow schedule requires new W0/P0-G security review, dedicated scheduled subject claims and actual triggered run validation.
4. Record screenshots / exported non-secret policy summary, reviewed-by, reviewed-at, and a decision (KEEP / REMEDIATE / HOLD). Do not paste credentials.

## Ops and evidence boundaries
- New GCS health report checks canonical four raw receipts and persisted cross-day receipt, writes Chinese GitHub Step Summary plus artifact; if any health check fails store fails.
- New failure-only Telegram job tries to send a short link-only message, and fails visibly when Telegram secrets are unavailable. A successful unit test does **not** prove Telegram delivery; controlled failure verification requires a separate approved procedure.
- Existing `shadow-outcome-backfill.yml` has its own weekday schedule and `sky-research-signal-evidence.yml` is scanner-triggered. Do not add another outcome or trading-signal schedule blindly.
- Research event first-observed timestamp is not issuer original published_at. Historic event PIT=UNKNOWN; 0 eligible event trades, no Production signal or auto-order, no positive expectancy claim.

## Remaining exit criteria
1. Bucket admin settings evidenced and explicitly approved (immutable retention only if policy agrees; do not lock bucket impulsively).
2. One main `workflow_dispatch` AFTER health PR merged; validate `GCS_RESEARCH_EVIDENCE_HEALTH_PASS` and upload artifact, no real trades.
3. Verify failure-alert route via safe controlled failure / already available failed operational run, without forging market evidence.
4. Design separate scheduled-identity WIF + exchange only after security review; avoid schedule pretending success without live schedule run.
5. Link forward research observation ID to **existing** P0-L decision ledger and W4 outcomes; never create a second canonical trade ledger. W4 must record genuine future trading days, outcome completeness >=95%, >=200 evaluable independent samples, >=2 market regimes and <=20% concentration before promotion review; W6 cost/fill proof and W0/P0-G are separate gates.
