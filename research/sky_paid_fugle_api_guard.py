"""Fail-closed, research-only cross-workflow paid API reservation.

All participating paid jobs MUST share the same GitHub Actions concurrency group.
Upload the claim artifact successfully BEFORE making any paid provider call.
Reservation blocks matching scope in the current/previous 5-minute UTC slots.
This is an operational anti-duplicate guard, NOT a market-data freshness cache.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

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
           "production_eligible": False, "automatic_order": False}
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "claim.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return allowed, artifact_name(scope, slots(now)[0]), out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scope", default=DEFAULT_SCOPE)
    p.add_argument("--verify", action="store_true")
    args = p.parse_args()
    now = datetime.now(timezone.utc)
    # A paid step must verify its own uploaded reservation is visible in GitHub.
    if args.verify:
        try:
            name = artifact_name(args.scope, slots(now)[0])
            own = [a for a in github_lookup(os.getenv("GITHUB_REPOSITORY", ""),
                                            os.getenv("GH_TOKEN", ""))(name)
                   if str(a.get("workflow_run", {}).get("id")) == os.getenv("GITHUB_RUN_ID")
                   and not a.get("expired", False)]
            if len(own) != 1:
                raise RuntimeError("OWN_RESERVATION_NOT_VISIBLE")
            print("FUGLE_RESERVATION_READBACK_VERIFIED:" + name)
            return
        except (ValueError, RuntimeError, HTTPError, URLError, TimeoutError, OSError) as exc:
            print("FUGLE_RESERVATION_READBACK_BLOCKED:" + type(exc).__name__)
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
