"""Read-only #363 Sky 警戒 bridge. Never fetches market quotes or runs a scanner."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from research.sky_alert_reader import consume

REPO = "cr8kj7k7j4-byte/sky-cloud-scanner"
WORKFLOW = "sky-chat-bridge.yml"
READONLY_COMMANDS = frozenset({"Sky 警戒", "Sky #363｜查詢最近一次掃描報告"})


def gh_json(route: str):
    return json.loads(subprocess.check_output(["gh", "api", route], text=True))


def select_source(*, current_run_id: str):
    """Prefer the latest completed successful paid scan with a matching published artifact."""
    route = f"repos/{REPO}/actions/workflows/{WORKFLOW}/runs?status=success&per_page=35"
    for run in gh_json(route).get("workflow_runs", []):
        run_id = str(run.get("id", ""))
        if (run_id == str(current_run_id) or run.get("conclusion") != "success"
                or run.get("event") not in ("issue_comment", "workflow_dispatch", "push")):
            continue
        artifacts = gh_json(f"repos/{REPO}/actions/runs/{run_id}/artifacts").get("artifacts", [])
        expected = f"sky-chat-{run_id}-attempt-{run.get('run_attempt')}"
        for artifact in artifacts:
            if (artifact.get("name") == expected and not artifact.get("expired")
                    and int(artifact.get("id", 0)) > 0):
                return run, artifact
    raise ValueError("NO_VERIFIED_EXISTING_SCAN_ARTIFACT")


def find_source_json(target: Path) -> Path:
    """Accept only documented layout variants of the same named source file.

    upload-artifact may trim the common `output/` ancestor.  Never select
    an unrelated JSON or substitute an unverified status-only receipt.
    """
    candidates = [
        target / "output/sky_quickscan_information/full_universe.json",
        target / "sky_quickscan_information/full_universe.json",
        target / "full_universe.json",
    ]
    found = [path for path in candidates if path.is_file()]
    if len(found) != 1:
        raise ValueError("SOURCE_FULL_UNIVERSE_NOT_FOUND_OR_AMBIGUOUS")
    return found[0]


def make_receipt(source, *, run_id: str, run_attempt: str, head_sha: str,
                 comment_id: str, source_provenance: dict, command: str = "Sky 警戒"):
    if command not in READONLY_COMMANDS:
        raise ValueError("UNAUTHORIZED_READBACK_COMMAND")
    evaluated = consume(source)
    if evaluated.get("production_eligible") is not False or evaluated.get("action") != "禁止交易":
        raise ValueError("ALERT_SAFETY_INVARIANT_FAILED")
    return {
        "schema": "SKY_ALERT_CHAT_RECEIPT_V1",
        "command": command,
        "run_id": run_id,
        "run_attempt": int(run_attempt),
        "head_sha": head_sha,
        "request_comment_id": comment_id,
        "source": source_provenance,
        "read_at_tpe": evaluated["read_at_tpe"],
        "source_checked_at_tpe": evaluated.get("source_checked_at_tpe"),
        "source_age_seconds": evaluated.get("source_age_seconds"),
        "freshness_status": evaluated["freshness_status"],
        "fresh_executed_count_at_read": evaluated.get("fresh_executed_count_at_read", 0),
        "universe_count": len(evaluated.get("report", {}).get("all_symbols", [])),
        "observation_available": evaluated.get("observation_available") is True,
        "production_eligible": False,
        "automatic_order": False,
        "trade_action": "禁止交易",
    }


def run():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--markdown", type=Path, required=True)
    args = ap.parse_args()
    run_id = os.environ["GITHUB_RUN_ID"]
    attempt = os.environ["GITHUB_RUN_ATTEMPT"]
    sha = os.environ["GITHUB_SHA"]
    repo = os.environ["GITHUB_REPOSITORY"]
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    comment = event.get("comment") or {}
    issue = event.get("issue") or {}
    authorized = (
        repo == REPO and event.get("repository", {}).get("full_name") == REPO
        and issue.get("number") == 363 and comment.get("body") in READONLY_COMMANDS
        and comment.get("user", {}).get("login") == REPO.split("/")[0]
        and comment.get("author_association") == "OWNER"
        and str(comment.get("id", "")).isdigit()
    )
    if not authorized:
        raise ValueError("UNAUTHORIZED_SKY_ALERT_EVENT")
    source_run, artifact = select_source(current_run_id=run_id)
    source_id = str(source_run["id"])
    name = artifact["name"]
    target = Path("/tmp/sky-alert-existing-source")
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["gh", "run", "download", source_id, "--repo", REPO,
         "--name", name, "--dir", str(target)], check=True
    )
    source_path = find_source_json(target)
    raw = source_path.read_bytes()
    source = json.loads(raw)
    provenance = {
        "repo": REPO,
        "source_run_id": source_id,
        "source_run_attempt": source_run["run_attempt"],
        "source_head_sha": source_run["head_sha"],
        "source_artifact_id": artifact["id"],
        "source_artifact_name": name,
        "source_json_sha256": hashlib.sha256(raw).hexdigest(),
    }
    receipt = make_receipt(
        source, run_id=run_id, run_attempt=attempt, head_sha=sha,
        comment_id=str(comment["id"]), source_provenance=provenance,
        command=comment["body"]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(
        "# " + comment["body"] + "｜既有 Artifact 唯讀查核\n\n"
        + f"本次 Run：{run_id}；來源 Run：{source_id}；來源 Artifact：{artifact['id']}\n\n"
        + f"資料時間：{receipt['source_checked_at_tpe']}；讀取時間：{receipt['read_at_tpe']}\n\n"
        + f"新鮮度：{receipt['freshness_status']}；有效成交驗證：{receipt['fresh_executed_count_at_read']}\n\n"
        + "**禁止交易。歷史快照不等於即時成交；未經 W0／P0-G 核准不得進場。**\n",
        encoding="utf-8",
    )
    print("SKY_ALERT_RESEARCH_READ_ONLY", receipt["freshness_status"])
    print("SKY_ALERT_SOURCE_RUN", source_id, "ARTIFACT", artifact["id"])


if __name__ == "__main__":
    run()
