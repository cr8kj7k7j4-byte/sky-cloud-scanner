"""W0 read-only GitHub Actions discovery. Never calls Fugle or triggers scans."""
from __future__ import annotations
import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SCHEMA = "SKY_W0_RUN_DISCOVERY_V1"
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA = re.compile(r"^[0-9a-f]{40}$")


def parse_time(value):
    if not isinstance(value, str):
        raise ValueError("TIMESTAMP_MISSING")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("TIMESTAMP_TZ_REQUIRED")
    return result.astimezone(timezone.utc)


def github_json(repo, token, endpoint):
    if not REPO.fullmatch(repo) or not token or not endpoint.startswith("/") or endpoint.startswith("//"):
        raise ValueError("GITHUB_ACCESS_INVALID")
    req = Request(
        "https://api.github.com/repos/" + repo + endpoint,
        headers={"Accept": "application/vnd.github+json", "Authorization": "Bearer " + token,
                 "X-GitHub-Api-Version": "2022-11-28"})
    with urlopen(req, timeout=15) as response:
        return json.load(response)


def discover(repo, token, comment_id, start, end, getter=github_json, max_pages=5):
    if end <= start or (end - start).total_seconds() > 86400 or comment_id <= 0:
        raise ValueError("INVALID_WINDOW_OR_COMMENT")
    comment = getter(repo, token, "/issues/comments/" + str(comment_id))
    if not isinstance(comment, dict) or comment.get("id") != comment_id:
        raise ValueError("COMMENT_ID_MISMATCH")
    # A dispatch-provided comment ID must refer to the canonical W0 issue
    # and its repository owner, not merely match a timestamp or numeric ID.
    author = comment.get("user")
    expected_issue = "https://api.github.com/repos/" + repo + "/issues/363"
    if (comment.get("issue_url") != expected_issue
        or not isinstance(author, dict)
        or author.get("login") != repo.split("/", 1)[0]
        or comment.get("author_association") != "OWNER"):
        raise ValueError("COMMENT_SOURCE_NOT_OWNER_363")
    comment_time = parse_time(comment.get("created_at"))
    if comment_time > end:
        raise ValueError("COMMENT_AFTER_WINDOW")
    candidates, complete, listed_count, expected_total = [], False, 0, None
    seen_run_ids = set()
    for page in range(1, max_pages + 1):
        query = urlencode({"per_page": 100, "page": page,
                           "created": start.strftime("%Y-%m-%dT%H:%M:%SZ") + ".." +
                                      end.strftime("%Y-%m-%dT%H:%M:%SZ")})
        response = getter(repo, token, "/actions/runs?" + query)
        batch = response.get("workflow_runs") if isinstance(response, dict) else None
        if not isinstance(batch, list):
            raise ValueError("INVALID_RUN_LIST")
        total = response.get("total_count")
        if type(total) is not int or total < 0:
            raise ValueError("INVALID_RUN_LIST_TOTAL")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise ValueError("RUN_LIST_TOTAL_CHANGED")
        listed_count += len(batch)
        if listed_count > expected_total:
            raise ValueError("RUN_LIST_TOTAL_MISMATCH")
        for run in batch:
            if not isinstance(run, dict):
                raise ValueError("INVALID_RUN")
            listed_run_id = run.get("id")
            if type(listed_run_id) is not int or listed_run_id <= 0:
                raise ValueError("INVALID_RUN_IDENTITY")
            if listed_run_id in seen_run_ids:
                raise ValueError("DUPLICATE_RUN_ID")
            seen_run_ids.add(listed_run_id)
            stamp = parse_time(run.get("created_at"))
            if run.get("event") != "issue_comment" or not start <= stamp <= end:
                continue
            run_id, head = run.get("id"), run.get("head_sha")
            if type(run_id) is not int or run_id <= 0 or not SHA.fullmatch(str(head or "")):
                raise ValueError("INVALID_RUN_IDENTITY")
            # Run attempt and workflow identity are required to interpret a
            # candidate event. Missing/boolean/nonpositive identifiers cannot
            # be promoted to credible provenance even at research level.
            attempt = run.get("run_attempt")
            workflow_id = run.get("workflow_id")
            workflow_name = run.get("name")
            if (type(attempt) is not int or attempt <= 0
                or type(workflow_id) is not int or workflow_id <= 0
                or not isinstance(workflow_name, str) or not workflow_name.strip()):
                raise ValueError("INVALID_WORKFLOW_RUN_METADATA")
            artifact_response = getter(repo, token, "/actions/runs/" + str(run_id) + "/artifacts?per_page=100")
            artifacts = artifact_response.get("artifacts") if isinstance(artifact_response, dict) else None
            total = artifact_response.get("total_count") if isinstance(artifact_response, dict) else None
            if (not isinstance(artifacts, list) or type(total) is not int
                or total != len(artifacts) or total < 0):
                raise ValueError("INCOMPLETE_ARTIFACT_LIST")
            if any(
                not isinstance(a, dict)
                or type(a.get("id")) is not int or a["id"] <= 0
                or not isinstance(a.get("name"), str) or not a["name"]
                for a in artifacts
            ):
                raise ValueError("INVALID_ARTIFACT_IDENTITY")
            if len({a["id"] for a in artifacts}) != len(artifacts):
                raise ValueError("DUPLICATE_ARTIFACT_ID")
            candidates.append({
                "run_id": run_id, "workflow": workflow_name, "workflow_id": workflow_id,
                "event": run.get("event"), "status": run.get("status"),
                "conclusion": run.get("conclusion"), "created_at": stamp.isoformat(),
                "head_sha": head, "attempt": attempt,
                "artifacts": [{"id": a.get("id"), "name": a.get("name"), "digest": a.get("digest"),
                               "created_at": a.get("created_at"), "expired": a.get("expired")}
                              for a in artifacts if isinstance(a, dict)]
            })
        if len(batch) < 100:
            complete = listed_count == expected_total
            break
    # A run matching a time window is NOT proof that the original comment
    # caused it. Only an event-attested same-run receipt can certify linkage.
    return {"schema": SCHEMA, "target_comment_id": comment_id,
            "target_comment_created_at": comment_time.isoformat(),
            "window_start_utc": start.isoformat(), "window_end_utc": end.isoformat(),
            "listing_complete": complete, "candidate_runs": candidates,
            "comment_to_run_status": "HOLD_UNCORRELATED",
            "market_capture_status": "HOLD_UNVERIFIED",
            "status": ("HOLD_LISTING_INCOMPLETE" if not complete else
                       "HOLD_CANDIDATE_RUN_UNCORRELATED" if candidates else
                       "HOLD_NO_MATCHING_RUN"),
            "production_eligible": False, "automatic_order": False,
            "trade_action": "禁止交易"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--comment-id", type=int, required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", default="output/w0_evidence/run_discovery.json")
    args = parser.parse_args()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = discover(os.getenv("GITHUB_REPOSITORY", ""), os.getenv("GH_TOKEN", ""),
                          args.comment_id, parse_time(args.start), parse_time(args.end))
    except Exception as exc:
        result = {"schema": SCHEMA, "target_comment_id": args.comment_id,
                  "status": "HOLD_DISCOVERY_FAILED", "error_type": type(exc).__name__,
                  "production_eligible": False, "automatic_order": False,
                  "trade_action": "禁止交易"}
    result["discovery_run_id"] = os.getenv("GITHUB_RUN_ID")
    result["discovery_head_sha"] = os.getenv("GITHUB_SHA")
    result["discovery_event"] = os.getenv("GITHUB_EVENT_NAME")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "run_id": result.get("discovery_run_id")}))


if __name__ == "__main__":
    main()
