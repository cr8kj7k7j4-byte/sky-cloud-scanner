"""Fail-closed, research-only cross-workflow paid API reservation.

All participating paid jobs MUST share the same GitHub Actions concurrency group.
Upload the claim artifact successfully BEFORE making any paid provider call.
Reservation blocks matching scope in the current/previous 5-minute UTC slots.
This is an operational anti-duplicate guard, NOT a market-data freshness cache.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import secrets
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener

WINDOW_SECONDS = 300
CLAIM_DIR = Path("output/fugle_api_guard")
DEFAULT_SCOPE = "paid-fugle-global-research"


def artifact_name(scope: str, slot: int) -> str:
    if not scope or len(scope) > 128:
        raise ValueError("INVALID_SCOPE")
    digest = hashlib.sha256(scope.encode("utf-8")).hexdigest()[:16]
    return f"sky-fugle-reservation-{digest}-{slot}"


def slots(now: datetime) -> tuple[int, int]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("NAIVE_TIMESTAMP")
    current = int(now.timestamp()) // WINDOW_SECONDS
    return current, current - 1


def check_reservation(scope: str, now: datetime, lookup) -> tuple[bool, str]:
    """lookup(name) returns a list of GitHub artifact metadata or raises.

    Fail closed for malformed/error responses. Expired artifacts from the
    previous slot do not block once older than WINDOW_SECONDS.
    """
    current, previous = slots(now)
    for slot in (current, previous):
        artifacts = lookup(artifact_name(scope, slot))
        if not isinstance(artifacts, list):
            raise RuntimeError("INVALID_ARTIFACT_RESPONSE")
        for a in artifacts:
            if not isinstance(a, dict) or not isinstance(a.get("created_at"), str):
                raise RuntimeError("INVALID_ARTIFACT_METADATA")
            created = datetime.fromisoformat(a["created_at"].replace("Z", "+00:00"))
            if created.tzinfo is None:
                raise RuntimeError("NAIVE_ARTIFACT_TIME")
            age = (now - created).total_seconds()
            if -30 <= age < WINDOW_SECONDS:
                return False, "RECENT_RESERVATION"
            if age < -30:
                raise RuntimeError("FUTURE_ARTIFACT_TIMESTAMP")
    return True, "CLEAR"


def github_lookup(repo: str, token: str):
    if not repo or len(repo.split("/")) != 2 or not token:
        raise RuntimeError("MISSING_GITHUB_AUTH")
    def lookup(name: str):
        url = f"https://api.github.com/repos/{repo}/actions/artifacts?name={quote(name)}&per_page=100"
        request = Request(url, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Sky-Fugle-Dedup-Guard",
        })
        with urlopen(request, timeout=12) as resp:
            result = json.load(resp)
        if not isinstance(result, dict) or not isinstance(result.get("artifacts"), list):
            raise RuntimeError("INVALID_GITHUB_RESPONSE")
        if result.get("total_count", 0) > len(result["artifacts"]):
            # A truncated response must never accidentally permit a call.
            raise RuntimeError("TRUNCATED_GITHUB_ARTIFACT_RESPONSE")
        return result["artifacts"]
    return lookup


def prepare(scope: str, now: datetime, lookup, run_id: str, outdir: Path):
    allowed, reason = check_reservation(scope, now, lookup)
    out = {"schema": "SKY_PAID_FUGLE_RESERVATION_V1",
           "status": "CLAIM_REQUIRED_BEFORE_PAID_API" if allowed else "DUPLICATE_BLOCKED",
           "reason": reason, "scope_hash": hashlib.sha256(scope.encode()).hexdigest()[:16],
           "slot": slots(now)[0], "run_id": run_id, "checked_at_utc": now.isoformat(),
           "claim_nonce": secrets.token_hex(16),
           "production_eligible": False, "automatic_order": False}
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "claim.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return allowed, artifact_name(scope, slots(now)[0]), out


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download_claim_archive(repo: str, token: str, artifact_id: int) -> dict:
    """Read actual GitHub Artifact ZIP, without forwarding GitHub credentials to storage."""
    if not repo or not token or type(artifact_id) is not int or artifact_id <= 0:
        raise RuntimeError("INVALID_ARTIFACT_DOWNLOAD_ARGUMENTS")
    api = f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}/zip"
    req = Request(api, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "Sky-Fugle-Dedup-Guard",
    })
    try:
        with build_opener(_NoRedirect).open(req, timeout=15):
            raise RuntimeError("EXPECTED_ARTIFACT_ZIP_REDIRECT")
    except HTTPError as exc:
        if exc.code not in (302, 307):
            raise
        location = exc.headers.get("Location", "")
    url = urlparse(location)
    allowed_hosts = (".blob.core.windows.net", ".actions.githubusercontent.com",
                     ".githubusercontent.com")
    if url.scheme != "https" or not any(
        url.hostname and url.hostname.endswith(suffix) for suffix in allowed_hosts
    ):
        raise RuntimeError("UNTRUSTED_ARTIFACT_DOWNLOAD_REDIRECT")
    # This request intentionally has NO GitHub authorization header.
    with urlopen(Request(location, headers={"User-Agent": "Sky-Fugle-Dedup-Guard"}),
                 timeout=15) as resp:
        raw = resp.read(262145)
    if len(raw) > 262144:
        raise RuntimeError("OVERSIZED_CLAIM_ARCHIVE")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            names = zf.namelist()
            if names != ["claim.json"]:
                raise RuntimeError("UNEXPECTED_ARTIFACT_ARCHIVE_CONTENTS")
            with zf.open("claim.json") as member:
                value = json.loads(member.read(16385))
    except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("INVALID_CLAIM_ARCHIVE") from exc
    if not isinstance(value, dict):
        raise RuntimeError("INVALID_CLAIM_DOCUMENT")
    return value


def verify_uploaded_reservation(scope: str, run_id: str, now: datetime,
                                local: dict, lookup, download) -> str:
    """Never accept another Job's Artifact merely because its run_id is equal."""
    if not isinstance(local, dict) or local.get("schema") != "SKY_PAID_FUGLE_RESERVATION_V1":
        raise RuntimeError("INVALID_LOCAL_CLAIM")
    if local.get("status") != "CLAIM_REQUIRED_BEFORE_PAID_API":
        raise RuntimeError("LOCAL_RESERVATION_NOT_ALLOWED")
    if local.get("run_id") != run_id or not run_id:
        raise RuntimeError("CLAIM_RUN_MISMATCH")
    if not isinstance(local.get("claim_nonce"), str) or len(local["claim_nonce"]) != 32:
        raise RuntimeError("INVALID_LOCAL_NONCE")
    ts = datetime.fromisoformat(str(local.get("checked_at_utc", "")).replace("Z", "+00:00"))
    age = (now - ts).total_seconds()
    if ts.tzinfo is None or not (-30 <= age < WINDOW_SECONDS):
        raise RuntimeError("CLAIM_EXPIRED_OR_FUTURE")
    slot = slots(ts)[0]
    if local.get("slot") != slot:
        raise RuntimeError("CLAIM_SLOT_MISMATCH")
    if local.get("scope_hash") != hashlib.sha256(scope.encode()).hexdigest()[:16]:
        raise RuntimeError("CLAIM_SCOPE_MISMATCH")
    name = artifact_name(scope, slot)
    own = [a for a in lookup(name)
           if str((a.get("workflow_run") or {}).get("id")) == run_id
           and not a.get("expired", False)]
    if len(own) != 1:
        raise RuntimeError("OWN_RESERVATION_NOT_VISIBLE")
    artifact_id = own[0].get("id")
    remote = download(artifact_id)
    for key in ("schema", "status", "claim_nonce", "scope_hash", "slot", "run_id"):
        if remote.get(key) != local.get(key):
            raise RuntimeError("ARTIFACT_CLAIM_CONTENT_MISMATCH_" + key)
    return name


def workflow_request_scope(workflow: str, event: dict) -> str:
    """Distinct inputs must not be treated as duplicate paid requests.

    This is a workflow-level fallback, NOT endpoint-level cross-workflow dedup.
    """
    if not workflow or not isinstance(event, dict):
        raise ValueError("INVALID_WORKFLOW_REQUEST")
    inputs = event.get("inputs")
    if inputs is None:
        inputs = {}
    if not isinstance(inputs, dict):
        raise ValueError("INVALID_WORKFLOW_INPUTS")
    identity_input = dict(inputs)
    if event.get("after") and isinstance(event.get("after"), str):
        identity_input["_push_after_sha"] = event["after"]
    normalized = json.dumps(identity_input, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":"))
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
    identity = hashlib.sha256(workflow.encode("utf-8")).hexdigest()[:16]
    return f"sky:paid:workflow:{identity}:{digest}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scope", default=DEFAULT_SCOPE)
    p.add_argument("--workflow-scope", action="store_true")
    p.add_argument("--verify", action="store_true")
    args = p.parse_args()
    now = datetime.now(timezone.utc)
    if args.workflow_scope:
        try:
            event_file = Path(os.environ["GITHUB_EVENT_PATH"])
            event = json.loads(event_file.read_text(encoding="utf-8"))
            args.scope = workflow_request_scope(
                os.environ["GITHUB_WORKFLOW"] + ":" + os.environ["GITHUB_EVENT_NAME"]
                + ":" + os.environ["GITHUB_REF"], event)
        except (OSError, KeyError, ValueError, TypeError) as exc:
            print("FUGLE_WORKFLOW_SCOPE_BLOCKED:" + type(exc).__name__)
            raise SystemExit(2) from None
    # A paid step must verify its own uploaded reservation is visible in GitHub.
    if args.verify:
        try:
            repo = os.getenv("GITHUB_REPOSITORY", "")
            token = os.getenv("GH_TOKEN", "")
            local = json.loads((CLAIM_DIR / "claim.json").read_text(encoding="utf-8"))
            lookup = github_lookup(repo, token)
            download = lambda artifact_id: download_claim_archive(repo, token, artifact_id)
            # Artifact indexing may lag the completed upload. Retry only the
            # specific missing-own-claim state; never retry a mismatched nonce.
            for attempt in range(4):
                try:
                    name = verify_uploaded_reservation(
                        args.scope, os.getenv("GITHUB_RUN_ID", ""),
                        datetime.now(timezone.utc), local, lookup, download)
                    print("FUGLE_RESERVATION_ZIP_CONTENT_READBACK_VERIFIED:" + name)
                    return
                except RuntimeError as exc:
                    if str(exc) != "OWN_RESERVATION_NOT_VISIBLE" or attempt == 3:
                        raise
                    time.sleep(2)

        except (ValueError, RuntimeError, HTTPError, URLError, TimeoutError, OSError, zipfile.BadZipFile) as exc:
            code = str(exc) if type(exc) is RuntimeError and str(exc).isupper() and len(str(exc)) < 90 else type(exc).__name__
            print("FUGLE_RESERVATION_READBACK_BLOCKED:" + code)
            raise SystemExit(2) from None
    # No error or uncertain GitHub result may authorize paid queries.
    try:
        allowed, name, receipt = prepare(
            args.scope, now,
            github_lookup(os.getenv("GITHUB_REPOSITORY", ""), os.getenv("GH_TOKEN", "")),
            os.getenv("GITHUB_RUN_ID", ""), CLAIM_DIR)
    except (ValueError, RuntimeError, HTTPError, URLError, TimeoutError, OSError) as exc:
        print("FUGLE_PAID_GUARD_BLOCKED:" + type(exc).__name__)
        raise SystemExit(2) from None
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"allowed={'true' if allowed else 'false'}\nclaim_name={name}\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
