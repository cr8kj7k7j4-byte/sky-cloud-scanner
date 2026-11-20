"""Read-only W0 repository inventory of all workflow entrypoints and open PRs.

Classifies *suspected* duplicate cron/capability groups. Does NOT disable jobs,
delete research evidence, call Fugle, or authorize a live trade.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github/workflows"
OUT = ROOT / "output/w0_repo_dedup"

RETAIN_PROTECTED = {
    "scan.yml", "sky-full-market-five-minute-dispatch.yml",
    "sky-full-market-private.yml", "sky-chat-bridge.yml",
    "schedule-health-audit.yml", "research-freeze-governance.yml",
    "sky-paper-only-acceptance.yml", "sky-recovery-watchdog.yml",
}
REMOVED = {
    "sky-research-once-20261109.yml",
    "sky-overnight-readiness-watch-20261109.yml",
    "sky-overnight-13col-acceptance.yml",
    "sky-overnight-readonly-acceptance-20261110.yml",
    "sky-preopen-watch-20261110.yml",
    "sky-preopen-evidence-monitor.yml",
}
CRON_RETIRED_KEEP_MANUAL = {
    "sky-research-ci-watchdog.yml",
    "w2-research-24h-watchdog.yml",
    "ai-direction-watchdog-5m.yml",
}
OWNERS = {
    "formal_execution_risk": {"lead": 365, "dependent": [367, 387],
                              "scope": "FUTURE_LIVE_ONLY; current research PAPER_ONLY is #496/#497/#498"},
    "fugle_quote_executed_provenance": {"lead": 480, "dependent": [357, 364, 472, 474, 499],
                                       "scope": "TWSE/TPEx source timestamps; no provider-paid duplicate"},
    "five_minute_causal_bars": {"lead": 488, "dependent": [480],
                               "scope": "5m timestamp causality; cannot fabricate certification"},
    "stock_13col_command_contract": {"lead": 421, "dependent": [425, 430, 435, 438],
                                    "scope": "one canonical route + independent six-model view"},
    "five_minute_scan_cadence": {"lead": None, "dependent": [373],
                                "scope": "both existing paid research and formal scan must be reconciled before removal"},
}
EXPIRED_CLOSED_PR = [253, 265, 355, 432, 437]


def _cron_from_workflow(src: str) -> list[str]:
    lines = src.splitlines()
    block_start = next((i for i, s in enumerate(lines)
                        if s.startswith("  schedule:")), None)
    if block_start is None:
        return []
    values = []
    for line in lines[block_start+1:]:
        if line.strip() and len(line)-len(line.lstrip()) <= 2:
            break
        if "cron:" in line:
            c = line.split("cron:", 1)[1].split("#", 1)[0].strip().strip("\"'")
            if c:
                values.append(c)
    return values


def _pr_snapshot():
    repo = os.getenv("GITHUB_REPOSITORY")
    if not repo or not os.getenv("GH_TOKEN"):
        return [], "PR_METADATA_NOT_QUERIED"
    try:
        p = subprocess.run(["gh", "api", "--paginate",
                            f"repos/{repo}/pulls?state=open&per_page=100"],
                           capture_output=True, text=True, timeout=40)
        if p.returncode:
            return [], "PR_METADATA_QUERY_FAILED"
        # gh --paginate may concatenate multiple JSON arrays; use jq stream
        # instead when needed. With <100 PR, first page remains one JSON array.
        data = json.loads(p.stdout)
        if not isinstance(data, list):
            return [], "PR_METADATA_INVALID"
        return [{"number": x["number"], "title": x["title"],
                 "draft": x.get("draft", False),
                 "head": x["head"]["sha"]} for x in data], "PR_API_CURRENT"
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        return [], "PR_METADATA_EXCEPTION"


def paid_workflow_overlap(workflows: list[dict]) -> dict:
    """Find structural paid API overlap; not proof of actual duplicate billing.

    GitHub concurrency groups only serialize their own group. Different event
    entrypoints may independently call Fugle in the same session, even after cron
    is paused. No provider calls are made by this audit.
    """
    paid = [w for w in workflows if w.get("paid_fugle_secret_referenced")]
    manual = sorted(w["name"] for w in paid if w.get("manual_dispatch"))
    push = sorted(w["name"] for w in paid if w.get("push_trigger"))
    schedules = sorted(w["name"] for w in paid if w.get("schedule_cron"))
    groups = {}
    for item in paid:
        group = item.get("concurrency_group")
        groups.setdefault(group or "NO_WORKFLOW_CONCURRENCY", []).append(item["name"])
    return {
        "paid_workflow_count": len(paid),
        "paid_workflow_names": sorted(w["name"] for w in paid),
        "manual_paid_entrypoints": manual,
        "push_paid_entrypoints": push,
        "scheduled_paid_entrypoints": schedules,
        "concurrency_groups": {k: sorted(v) for k, v in sorted(groups.items())},
        "cross_workflow_paid_api_dedup_certified": False,
        "runtime_paid_api_lease_verified": False,
        "provider_request_id_reconciliation_verified": False,
        "status": "HOLD_RUNTIME_LEDGER_AND_CROSS_WORKFLOW_LEASE_NOT_VERIFIED"
        if len(paid) > 1 else "INSUFFICIENT_RUNTIME_EVIDENCE",
        "note": "Possible simultaneous invocation, not actual duplicate calls or billing proof.",
    }


def audit(root: Path = ROOT, include_api: bool = False) -> dict:
    wf = root / ".github/workflows"
    paths = sorted(wf.glob("*.yml")) + sorted(wf.glob("*.yaml"))
    slots = defaultdict(list)
    entries = []
    for f in paths:
        src = f.read_text(encoding="utf-8")
        cron = _cron_from_workflow(src)
        item = {
            "path": str(f.relative_to(root)),
            "name": f.name,
            "schedule_cron": cron,
            "cron_count": len(cron),
            "paid_fugle_secret_referenced": "secrets.FUGLE_API_KEY" in src,
            "manual_dispatch": "  workflow_dispatch:" in src,
            "push_trigger": any(line.startswith("  push:") for line in src.splitlines()),
            "concurrency_group": next((
                line.strip().split("group:", 1)[1].strip()
                for line in src.splitlines()
                if line.startswith("  group:")
            ), None),
            "source_sha": "GIT_TRACKED_MAIN_OR_PR_HEAD",
        }
        entries.append(item)
        # Two cron expressions with the same string are a potential overlap,
        # NOT proof that jobs do the same work or cost duplicate API calls.
        for expr in cron:
            slots[expr].append(f.name)
    duplicates = [{"cron": c, "workflows": sorted(set(names))}
                  for c, names in sorted(slots.items())
                  if len(set(names)) > 1]
    prs, pr_verdict = _pr_snapshot() if include_api else ([], "PR_METADATA_NOT_QUERIED")
    missing_protected = sorted(RETAIN_PROTECTED - {x["name"] for x in entries})
    resurrected = sorted(REMOVED & {x["name"] for x in entries})
    expired_crons = sorted(name for name in CRON_RETIRED_KEEP_MANUAL
                           if any(x["name"] == name and x["cron_count"] for x in entries))
    return {
        "schema": "SKY_W0_DEDUP_REPOSITORY_AUDIT_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "workflow_count": len(entries),
        "workflow_list": entries,
        "workflow_with_schedule": sum(bool(x["schedule_cron"]) for x in entries),
        "potential_overlapping_cron_groups": duplicates,
        "paid_api_overlap": paid_workflow_overlap(entries),
        "overlapping_cron_not_equal_paid_api_duplication": True,
        "broker_account_required_for_research": False,
        "live_trading_enabled": False,
        "protected_workflows_missing": missing_protected,
        "removed_workflows_resurrected": resurrected,
        "expired_watchdog_crons_reintroduced": expired_crons,
        "open_pr_api_status": pr_verdict,
        "open_pr_count": len(prs) if pr_verdict == "PR_API_CURRENT" else None,
        "open_pr_details": prs,
        "canonical_pr_owners": OWNERS,
        "already_closed_duplicate_prs": EXPIRED_CLOSED_PR,
        "safe_bulk_delete_ready": False,
        "verdict": "HOLD_MANUAL_DEPENDENCY_REVIEW_REQUIRED",
        "note": "Structural inventory, not runtime invocation/cost proof. Preserve frozen research and live fail-closed gates.",
    }


def main():
    d = audit(include_api=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8")
    lines = ["# W0｜全庫 Workflow / PR 去重登錄", "",
             f"- Workflow：{d['workflow_count']}",
             f"- 有定時設定的 Workflow：{d['workflow_with_schedule']}",
             f"- 存在相同 cron 的群組：{len(d['potential_overlapping_cron_groups'])}",
             f"- PR 資料：{d['open_pr_api_status']}，開放 PR：{d['open_pr_count']}",
             f"- 付費 API 工作入口數：{d['paid_api_overlap']['paid_workflow_count']}",
             f"- 跨 Workflow 運行期去重：{d['paid_api_overlap']['status']}",
             f"- 已確認退場的舊入口回流：{d['removed_workflows_resurrected']}",
             f"- 到期 cron 回流：{d['expired_watchdog_crons_reintroduced']}",
             "", "## 疑似相同 cron（用途仍須對帳）"]
    for x in d["potential_overlapping_cron_groups"]:
        lines.append(f"- \`{x['cron']}\`：{', '.join(x['workflows'])}")
    lines += ["", "## 唯一整合責任 PR"]
    for k, v in OWNERS.items():
        lines.append(f"- {k}：主責 #{v['lead'] or '既有 main'}；相關 {v['dependent']}；{v['scope']}")
    lines += ["", "不因排程字串相同就宣稱重複付費；不刪研究負面證據；沒有券商開戶要求；實盤維持停用。"]
    (OUT / "latest.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
