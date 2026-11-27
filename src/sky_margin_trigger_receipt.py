"""Owner-only SKY維持率 GitHub issue-comment research receipt.

This deliberately does not fetch prices, query Fugle, scan stocks, or certify
caller-supplied sources. Missing authenticated data is an explicit HOLD.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

COMMAND = "SKY維持率"
SCHEMA = "SKY_MARGIN_COMMAND_HOLD_RECEIPT_V1"


def make_receipt(event: dict, *, repo: str, run_id: str, attempt: str, sha: str) -> dict:
    if not isinstance(event, dict):
        raise ValueError("INVALID_EVENT")
    issue = event.get("issue") or {}
    comment = event.get("comment") or {}
    repository = event.get("repository") or {}
    owner = repo.split("/", 1)[0] if isinstance(repo, str) else ""
    if (
        not repo or "/" not in repo
        or repository.get("full_name") != repo
        or issue.get("number") != 363
        or comment.get("body") != COMMAND
        or comment.get("author_association") != "OWNER"
        or (comment.get("user") or {}).get("login") != owner
        or not isinstance(comment.get("id"), int)
        or isinstance(comment.get("id"), bool)
        or comment["id"] <= 0
    ):
        raise ValueError("UNAUTHORIZED_MARGIN_TRIGGER")
    if not (run_id.isdecimal() and attempt.isdecimal()
            and int(run_id) > 0 and int(attempt) > 0
            and len(sha) == 40 and all(c in "0123456789abcdef" for c in sha.lower())):
        raise ValueError("INVALID_GITHUB_RUN_IDENTITY")
    return {
        "schema": SCHEMA,
        "command": COMMAND,
        "status": "HOLD_PRICE_ONLY_REAL_SOURCE_RUNNER_NOT_VERIFIED",
        "issue_number": 363,
        "trigger_comment_id": comment["id"],
        "repo": repo,
        "run_id": run_id,
        "attempt": attempt,
        "head_sha": sha,
        "source_type": "NONE_NO_MARKET_DATA_FETCHED",
        "market_scan_executed": False,
        "complete_official_universe_verified": False,
        "price_only_mode": True,
        "margin_ratio_screen_retired": True,
        "capital_and_prior_volume_screen_retired": True,
        "fugle_a2_verified": False,
        "provider_entitlement_verified": False,
        "price_only_live_runner_verified": False,
        "candidate_count": None,
        "mobile_e2e_verified": False,
        "production_eligible": False,
        "new_entry_authorized": False,
        "automatic_order": False,
        "trade_action": "禁止交易",
        "notice": "SKY維持率為舊指令名稱；已取消維持率推估、資本額及前日量篩選。價格觀察尚無真實資料及完整掃描驗證，禁止交易。",
    }


def verify_receipt(original: bytes, downloaded: bytes, *, run_id: str,
                   attempt: str, sha: str, comment_id: str) -> dict:
    if original != downloaded:
        raise ValueError("MARGIN_ARTIFACT_BYTES_MISMATCH")
    obj = json.loads(downloaded)
    if not (
        obj.get("schema") == SCHEMA
        and obj.get("command") == COMMAND
        and obj.get("run_id") == run_id
        and obj.get("attempt") == attempt
        and obj.get("head_sha") == sha
        and str(obj.get("trigger_comment_id")) == comment_id
        and obj.get("status") == "HOLD_PRICE_ONLY_REAL_SOURCE_RUNNER_NOT_VERIFIED"
        and obj.get("market_scan_executed") is False
        and obj.get("complete_official_universe_verified") is False
        and obj.get("fugle_a2_verified") is False
        and obj.get("new_entry_authorized") is False
        and obj.get("production_eligible") is False
        and obj.get("automatic_order") is False
        and obj.get("trade_action") == "禁止交易"
    ):
        raise ValueError("MARGIN_RECEIPT_IDENTITY_OR_SAFETY_MISMATCH")
    return {"status": "PASS_HOLD_RECEIPT_INTEGRITY_ONLY",
            "sha256": hashlib.sha256(downloaded).hexdigest(),
            "run_id": run_id, "attempt": attempt, "head_sha": sha,
            "trigger_comment_id": int(comment_id),
            "real_margin_scan_verified": False, "production_eligible": False,
            "trade_action": "禁止交易"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path)
    parser.add_argument("--repo")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--comment-id")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-original", type=Path)
    parser.add_argument("--verify-downloaded", type=Path)
    args = parser.parse_args(argv)
    if args.verify_original and args.verify_downloaded:
        result = verify_receipt(args.verify_original.read_bytes(),
                                args.verify_downloaded.read_bytes(),
                                run_id=args.run_id, attempt=args.attempt,
                                sha=args.sha, comment_id=args.comment_id or "")
    else:
        if not args.event or not args.repo:
            parser.error("event/repo required for produce")
        event = json.loads(args.event.read_text(encoding="utf-8"))
        result = make_receipt(event, repo=args.repo, run_id=args.run_id,
                              attempt=args.attempt, sha=args.sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
