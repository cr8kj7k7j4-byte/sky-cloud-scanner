"""Read a GitHub-hosted, precommitted PAPER_ONLY signal artifact, or HOLD.

Authenticates the run, SHA, artifact identity, and *actual GitHub upload time*
before allowing an existing receipt to be joined to already verified #512 bars.
Never creates a trading signal and never submits brokerage orders.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile

from research.sky_p0r_signal_bridge import join, _hold, _at


def _gh_api(endpoint):
    result = subprocess.run(
        ["gh", "api", endpoint], capture_output=True, text=True,
        check=True, timeout=25,
    )
    return json.loads(result.stdout)


def _receipt_from_github(repo, run_id, fetch=_gh_api, downloader=None):
    if not repo or "/" not in repo or not str(run_id).isdigit():
        raise ValueError("INVALID_GITHUB_PROVENANCE_INPUT")
    run = fetch(f"repos/{repo}/actions/runs/{run_id}")
    if (str(run.get("id")) != str(run_id)
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
            or run.get("repository", {}).get("full_name") != repo
            or not isinstance(run.get("head_sha"), str)
            or len(run["head_sha"]) != 40):
        raise ValueError("UNTRUSTED_SIGNAL_WORKFLOW_RUN")
    # Only an explicitly W0-approved signal-emitting workflow may provide
    # executable PAPER_ONLY research plans. A generic successful GitHub job
    # (for example a synthetic transport check) is never a signal authority.
    approved_workflow_id = os.getenv("SKY_P0R_APPROVED_SIGNAL_WORKFLOW_ID", "").strip()
    if (not approved_workflow_id.isdigit()
            or str(run.get("workflow_id")) != approved_workflow_id):
        raise ValueError("SIGNAL_WORKFLOW_NOT_GOVERNANCE_APPROVED")
    listing = fetch(f"repos/{repo}/actions/runs/{run_id}/artifacts")
    artifacts = listing.get("artifacts")
    name = f"sky-precommitted-paper-signal-{run_id}"
    matches = [a for a in (artifacts or []) if a.get("name") == name
               and str(a.get("workflow_run", {}).get("id")) == str(run_id)]
    if len(matches) != 1 or matches[0].get("expired") is not False:
        raise ValueError("PRECOMMITTED_SIGNAL_ARTIFACT_NOT_FOUND")
    artifact = matches[0]
    uploaded = _at(artifact.get("created_at"))
    if uploaded is None:
        raise ValueError("ARTIFACT_UPLOAD_TIME_UNAVAILABLE")
    if downloader is None:
        def downloader(destination):
            subprocess.run([
                "gh", "run", "download", str(run_id),
                "--repo", repo, "--name", name, "--dir", str(destination)
            ], capture_output=True, text=True, check=True, timeout=45)
    with tempfile.TemporaryDirectory(prefix="sky-p0r-signal-") as temp:
        downloader(Path(temp))
        receipt_file = Path(temp) / "precommitted_signal.json"
        if not receipt_file.is_file():
            raise ValueError("SIGNAL_RECEIPT_FILE_NOT_FOUND")
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    if (receipt.get("schema") != "SKY_PRECOMMITTED_PAPER_SIGNAL_V1"
            or str(receipt.get("signal_run_id")) != str(run_id)
            or receipt.get("signal_sha") != run["head_sha"]):
        raise ValueError("SIGNAL_RECEIPT_GITHUB_METADATA_MISMATCH")
    # GitHub assigns the Artifact ID *after* uploading its contents.
    # A precommitted receipt cannot truthfully contain that future ID.
    # If explicitly provided, verify it; otherwise attach only the ID
    # independently returned by GitHub after the successful upload.
    claimed_id = receipt.get("signal_artifact_id")
    if claimed_id is not None and str(claimed_id) != str(artifact["id"]):
        raise ValueError("SIGNAL_RECEIPT_GITHUB_METADATA_MISMATCH")
    receipt["signal_artifact_id"] = str(artifact["id"])
    original_published = _at(receipt.get("published_at"))
    signal_time = _at((receipt.get("signal") or {}).get("signal_time"))
    if original_published < signal_time:
        raise ValueError("SIGNAL_PUBLISHED_BEFORE_CREATION")
    # Local receipt timestamps are not proof of precommitment.
    # GitHub's artifact creation is the earliest independently verifiable commit.
    effective_published = max(original_published, uploaded)
    receipt["published_at"] = effective_published.isoformat()
    return receipt, {"signal_run_id": str(run_id), "signal_sha": run["head_sha"],
                     "signal_artifact_id": str(artifact["id"]),
                     "artifact_uploaded_at": uploaded.isoformat(),
                     "effective_published_at": effective_published.isoformat(),
                     "github_metadata_verified": True}


def main():
    bars_file = Path("output/sky_p0r_paper_ledger_readback/verified_512_completed_bars.json")
    output = Path("output/sky_p0r_paper_ledger_readback")
    output.mkdir(parents=True, exist_ok=True)
    source_run = None
    bars = None
    if bars_file.is_file():
        bars = json.loads(bars_file.read_text(encoding="utf-8"))
        source_run = bars.get("source_run_id")
    run_id = os.getenv("SKY_P0R_SIGNAL_RUN_ID", "").strip()
    status = None
    if not run_id:
        status = _hold("NO_EXTERNAL_PRECOMMITTED_SIGNAL_RUN_CONFIGURED",
                       source_run_id=source_run)
    elif bars is None:
        status = _hold("VERIFIED_MARKET_BARS_MISSING",
                       source_run_id=source_run, signal_run_id=run_id)
    else:
        try:
            receipt, provenance = _receipt_from_github(
                os.environ.get("GITHUB_REPOSITORY", ""), run_id)
            status, payload = join(
                bars, receipt, external_signal_provenance_verified=True,
                external_bar_provenance_verified=(
                    bars.get("github_bar_source_verified") is True))
            status["verified_github_provenance"] = provenance
            if payload is not None and status.get("reconciled") is True:
                target = Path("output/sky_paper_runtime/completed_market_evidence.json")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
                # Durable same-run source binding for downstream paper replay.
                # This receipt is NOT proof of real executions or live trading.
                canonical = json.dumps(
                    payload, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")).encode("utf-8")
                source_receipt = {
                    "schema": "SKY_P0R_PAPER_SOURCE_BINDING_V1",
                    "paper_input_sha256": hashlib.sha256(canonical).hexdigest(),
                    "market_run_id": bars["source_run_id"],
                    "market_sha": bars["source_sha"],
                    "market_artifact_id": bars["source_artifact_id"],
                    "market_observed_at": bars["observed_at"],
                    "signal_provenance": provenance,
                    "production_eligible": False,
                    "automatic_order": False,
                }
                (target.parent / "source_binding.json").write_text(
                    json.dumps(source_receipt, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
        except (ValueError, KeyError, TypeError, OSError,
                subprocess.CalledProcessError, subprocess.TimeoutExpired,
                json.JSONDecodeError) as exc:
            # An unavailable or untrusted external receipt must yield a durable
            # fail-closed Artifact, never a silent green paper-trade verdict.
            status = _hold("EXTERNAL_SIGNAL_READBACK_OR_PROVENANCE_FAILED",
                           source_run_id=source_run, signal_run_id=run_id)
            status["error_type"] = type(exc).__name__
    (output / "external_signal_source_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
