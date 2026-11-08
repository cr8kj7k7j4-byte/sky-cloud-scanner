"""Read-only Cloud Run revision attestation (no deploy, no market orders).

Produces a minimal sanitized report using actual gcloud describe responses.
The report never claims a healthy site based solely on a revision being ready.
"""
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SERVICE = "tw-ai-mobile"
REGION = "asia-east1"
IMMUTABLE_IMAGE_RE = re.compile(r"^[^\\s@]+@sha256:[0-9a-fA-F]{64}$")


def is_immutable_digest(value):
    return isinstance(value, str) and IMMUTABLE_IMAGE_RE.fullmatch(value) is not None

def extract(service, revision=None, revisions=None):
    if not isinstance(service, dict):
        raise ValueError("service_payload_missing")
    status = service.get("status") or {}
    metadata = service.get("metadata") or {}
    spec = service.get("spec") or {}
    if metadata.get("name") != SERVICE:
        raise ValueError("service_identity_mismatch")
    latest = status.get("latestReadyRevisionName")
    traffic = status.get("traffic") or []
    if (not isinstance(latest, str) or not latest.startswith(SERVICE + "-")
            or not isinstance(traffic, list) or not traffic):
        raise ValueError("missing_ready_revision_or_traffic")
    selected = []
    for row in traffic:
        if not isinstance(row, dict):
            raise ValueError("invalid_traffic")
        percent = row.get("percent", 0)
        if type(percent) is not int or percent < 0 or percent > 100:
            raise ValueError("invalid_traffic_percent")
        name = row.get("revisionName")
        # Cloud Run may represent a tagged latestRevision traffic target
        # without revisionName. Resolve it against the actual ready revision.
        if name is None and row.get("latestRevision") is True:
            name = latest
        if not isinstance(name, str) or not name.startswith(SERVICE + "-"):
            raise ValueError("invalid_traffic_revision")
        selected.append({"revision": name,
                         "percent": percent,
                         "tag": row.get("tag"),
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
    # Independently inspect every traffic revision, including tagged 0%-traffic
    # canaries. The service template does not attest a serving revision image.
    inspected = {}
    if revisions is not None:
        required = {latest} | {row["revision"] for row in selected}
        if set(revisions) != required:
            raise ValueError("revision_set_incomplete")
        for name in sorted(required):
            data = revisions[name]
            if not isinstance(data, dict) or (data.get("metadata") or {}).get("name") != name:
                raise ValueError("revision_identity_mismatch")
            containers = ((data.get("spec") or {}).get("containers") or [])
            spec_image = containers[0].get("image") if containers and isinstance(containers[0], dict) else None
            digest = (data.get("status") or {}).get("imageDigest")
            # Only container start configuration is attested. Never persist
            # environment variables, volumes, service account tokens or full
            # gcloud JSON, which can contain secret names and values.
            runtime = {
                "container_count": len(containers),
                "command_override_present": bool(containers[0].get("command")) if containers else False,
                "args_override_present": bool(containers[0].get("args")) if containers else False,
                "command_arg_count": len(containers[0].get("command") or []) if containers else 0,
                "args_count": len(containers[0].get("args") or []) if containers else 0,
                "first_container_ports": [
                    {"name": p.get("name"), "containerPort": p.get("containerPort")}
                    for p in (containers[0].get("ports") or []) if isinstance(p, dict)
                ] if containers and isinstance(containers[0], dict) else [],
                "revision_service_account_set": bool((data.get("spec") or {}).get("serviceAccountName")),
                "commit_label": (data.get("metadata") or {}).get("labels", {}).get("commit-sha"),
                "cloud_build_id_label": (data.get("metadata") or {}).get("labels", {}).get("gcb-build-id"),
            }
            inspected[name] = {"spec_image": spec_image, "status_image_digest": digest,
                               "image_evidence_present": bool(spec_image or digest),
                               "immutable_digest_present": is_immutable_digest(digest),
                               "runtime": runtime}
    conditions = status.get("conditions") or []
    ready = any(c.get("type") == "Ready" and c.get("status") == "True"
                for c in conditions if isinstance(c, dict))
    return {
        "service": metadata.get("name"),
        "ready_revision": latest,
        "traffic": selected,
        "service_template_image": image,
        "ready_revision_image_or_digest": rev_image,
        "revision_images": inspected,
        "all_revisions_inspected": revisions is not None,
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
        rows=(service.get("status") or {}).get("traffic") or []
        # Strictly bound service names; never query arbitrary caller-supplied IDs.
        names={rev}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("invalid_traffic_revision")
            name = row.get("revisionName")
            if name is None and row.get("latestRevision") is True:
                name = rev
            if not isinstance(name, str) or not name.startswith(SERVICE + "-"):
                raise ValueError("invalid_traffic_revision")
            names.add(name)
        revisions={name:gcloud_json("run","revisions","describe",name,"--region",REGION)
                   for name in sorted(names)}
        report["evidence"]=extract(service,revisions[rev],revisions)
        if not all(item["image_evidence_present"] for item in report["evidence"]["revision_images"].values()):
            raise ValueError("revision_image_evidence_missing")
        if not all(item["immutable_digest_present"] for item in report["evidence"]["revision_images"].values()):
            raise ValueError("revision_immutable_digest_missing")
        report["status"]="REVISION_READ_ONLY_CONFIRMED"
    except (ValueError,RuntimeError,subprocess.TimeoutExpired,json.JSONDecodeError) as ex:
        report["blocker"]=str(ex) if isinstance(ex,(ValueError,RuntimeError)) else type(ex).__name__
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Cloud Run revision attestation:",report["status"],
          "ready_revision:",report.get("evidence",{}).get("ready_revision","UNVERIFIED"))
    return 0 if report["status"]=="REVISION_READ_ONLY_CONFIRMED" else 2

if __name__=="__main__":
    raise SystemExit(main())
