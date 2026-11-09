"""Read-only readiness audit of existing Sky scans; no repairs, secrets or orders."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = "https://api.github.com/repos/"


def classify(run, health):
    """Separate pipeline execution from validated live-market eligibility."""
    status = run.get("status") if run else "missing"
    conclusion = run.get("conclusion") if run else None
    live_count = health.get("all_market_fresh_executed_count")
    observed = health.get("all_market_observed_price_count")
    universe = health.get("all_market_universe_count")
    return {
        "scanner_status": status,
        "scanner_conclusion": conclusion,
        "scanner_run_id": run.get("id") if run else None,
        "market_universe": universe,
        "snapshot_observed": observed,
        "snapshot_fresh_executed": live_count,
        "snapshot_trade_eligible": bool(health.get("trade_eligible") is True),
        "market_live_verified": bool(health.get("trade_eligible") is True and live_count and universe and live_count == universe),
        "report_status": "available" if health.get("run_id") else "missing",
        "readiness": "PASS" if conclusion == "success" and health.get("trade_eligible") is True and live_count and universe and live_count == universe else "BLOCKED",
    }


def fetch_json(url, token):
    request = urllib.request.Request(
        url, headers={"Authorization": "Bearer " + token,
                      "Accept": "application/vnd.github+json",
                      "User-Agent": "sky-readiness-audit"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def main():
    token = os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or "/" not in repo:
        raise SystemExit("github_context_required")
    root = ROOT + repo
    runs = fetch_json(root + "/actions/workflows/scan.yml/runs?per_page=6", token).get("workflow_runs", [])
    latest = next((r for r in runs if r.get("status") == "completed"), None)
    health = {}
    try:
        content = fetch_json(root + "/contents/docs/SKY_MCR_INTRADAY_HEALTH_LATEST.json", token)
        import base64
        health = json.loads(base64.b64decode(content.get("content", "")).decode("utf-8"))
    except (KeyError, ValueError, UnicodeDecodeError):
        health = {}
    result = classify(latest, health)
    result.update({
        "schema": "SKY_READINESS_AUDIT_V1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "GitHub Actions run metadata + sanitized MCR health",
        "scan_url": latest.get("html_url") if latest else None,
        "snapshot_health_run_id": health.get("run_id"),
        "note": "Read-only audit; PASS does not alone authorize trading; overnight market cannot be certified live.",
        "no_orders_or_production_change": True,
    })
    folder = Path("recovery-reports")
    folder.mkdir(exist_ok=True)
    (folder / "intraday_readiness.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
