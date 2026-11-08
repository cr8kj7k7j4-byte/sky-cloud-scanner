"""Read-only Cloud Run revision attestation (no deploy, no market orders).

Produces a minimal sanitized report using actual gcloud describe responses.
The report never claims a healthy site based solely on a revision being ready.
"""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SERVICE = "tw-ai-mobile"
REGION = "asia-east1"

def extract(service, revision=None):
    if not isinstance(service, dict):
        raise ValueError("service_payload_missing")
    status = service.get("status") or {}
    metadata = service.get("metadata") or {}
    spec = service.get("spec") or {}
    latest = status.get("latestReadyRevisionName")
    traffic = status.get("traffic") or []
    if not latest or not isinstance(traffic, list):
        raise ValueError("missing_ready_revision_or_traffic")
    selected = []
    for row in traffic:
        if not isinstance(row, dict):
            raise ValueError("invalid_traffic")
        percent = row.get("percent", 0)
        if not isinstance(percent, int) or percent < 0 or percent > 100:
            raise ValueError("invalid_traffic_percent")
        selected.append({"revision": row.get("revisionName"),
                         "percent": percent,
                         "latest_revision": row.get("latestRevision") is True})
    if sum(row["percent"] for row in selected) != 100:
        raise ValueError("traffic_not_fully_attributed")
    template = (spec.get("template") or {}).get("spec") or {}
    containers = template.get("containers") or []
    image = containers[0].get("image") if containers and isinstance(containers[0],dict) else None
    rev_image = None
    if isinstance(revision,dict):
        candidates = ((revision.get("spec") or {}).get("containers") or [])
        if candidates and isinstance(candidates[0],dict):
            rev_image = candidates[0].get("image")
        rev_image = ((revision.get("status") or {}).get("imageDigest")
                     or rev_image)
    conditions = status.get("conditions") or []
    ready = any(c.get("type") == "Ready" and c.get("status") == "True"
                for c in conditions if isinstance(c, dict))
    return {
        "service": metadata.get("name"),
        "ready_revision": latest,
        "traffic": selected,
        "service_template_image": image,
        "ready_revision_image_or_digest": rev_image,
        "service_ready_condition": ready,
        "deployed_commit": "UNVERIFIED_NO_TRUSTED_BUILD_ATTESTATION",
        "http_health_verified": False,
        "authenticated_routes_verified": False,
        "trade_authorized": False,
    }

def gcloud_json(*args):
    result = subprocess.run(["gcloud", *args, "--format=json"],
                            capture_output=True, text=True, timeout=45)
    if result.returncode:
        # Do not leak full gcloud stderr, which might include local environment details.
        raise RuntimeError("GCLOUD_DESCRIBE_FAILED_EXIT_" + str(result.returncode))
    return json.loads(result.stdout)

def main():
    out=Path("output/cloud_run_revision_readonly_audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    report={"schema": "sky-cloudrun-readonly-revision-v1",
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "BLOCKED", "production_changed": False,
            "deployment_performed": False, "trading_enabled": False}
    try:
        service=gcloud_json("run","services","describe",SERVICE,"--region",REGION)
        rev=(service.get("status") or {}).get("latestReadyRevisionName")
        if not rev:
            raise ValueError("missing_ready_revision")
        revision=gcloud_json("run","revisions","describe",rev,"--region",REGION)
        report["evidence"]=extract(service,revision)
        report["status"]="REVISION_READ_ONLY_CONFIRMED"
    except (ValueError,RuntimeError,subprocess.TimeoutExpired,json.JSONDecodeError) as ex:
        report["blocker"]=str(ex) if isinstance(ex,(ValueError,RuntimeError)) else type(ex).__name__
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Cloud Run revision attestation:",report["status"],
          "ready_revision:",report.get("evidence",{}).get("ready_revision","UNVERIFIED"))
    return 0 if report["status"]=="REVISION_READ_ONLY_CONFIRMED" else 2

if __name__=="__main__":
    raise SystemExit(main())
