"""Fail-closed GCS research evidence health summary from upload/ledger receipts.

This is not a strategy scorecard. Do not infer true filing timestamps,
real-world fills, realized P&L, or Production promotion from snapshots.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from research.disclosure_gcs_readback import REQUIRED


def safe_health(raw, ledger):
    if not isinstance(raw, dict) or not isinstance(ledger, dict):
        raise ValueError("RECEIPTS_REQUIRED")
    if raw.get("state") != "GCS_READBACK_VERIFIED":
        raise ValueError("SOURCE_GCS_READBACK_NOT_VERIFIED")
    sources = raw.get("objects")
    if (not isinstance(sources, dict) or set(sources) != set(REQUIRED)
            or any(not isinstance(v, dict) or v.get("readback_verified") is not True
                   or len(str(v.get("sha256", ""))) != 64 for v in sources.values())):
        raise ValueError("FOUR_SOURCE_HASH_RECEIPTS_INVALID")
    if ledger.get("status") != "GCS_CROSSDAY_LEDGER_READBACK_PASS":
        raise ValueError("CROSSDAY_LEDGER_NOT_VERIFIED")
    if not isinstance(ledger.get("source_batches"), int) or ledger["source_batches"] < 1:
        raise ValueError("NO_COMMITTED_SOURCE_BATCH")
    if not isinstance(ledger.get("unique_provisional_events"), int) or ledger["unique_provisional_events"] < 0:
        raise ValueError("INVALID_EVENT_COUNT")
    if (raw.get("production_signal") is not False or ledger.get("production_signal") is not False
            or ledger.get("eligible_trade_events") != 0
            or ledger.get("issuer_original_published_at_verified") is not False):
        raise ValueError("RESEARCH_PIT_SAFETY_GATE_BROKEN")
    if not isinstance(ledger.get("object_path"), str) or not ledger["object_path"].startswith("disclosure-forward-ledgers/v1/run-"):
        raise ValueError("INVALID_LEDGER_EVIDENCE_PATH")
    if ledger.get("retention_iam_gate") != "NOT_VERIFIED":
        raise ValueError("UNSUPPORTED_POLICY_ATTESTATION")
    return {
        "status": "GCS_RESEARCH_EVIDENCE_HEALTH_PASS",
        "source_batches": ledger["source_batches"],
        "unique_provisional_events": ledger["unique_provisional_events"],
        "unchanged": (ledger.get("cumulative_counts") or {}).get("unchanged"),
        "revision": (ledger.get("cumulative_counts") or {}).get("revision"),
        "skipped_invalid": (ledger.get("cumulative_counts") or {}).get("skipped_invalid"),
        "gcs_raw_prefix": raw.get("prefix"),
        "gcs_ledger_path": ledger.get("object_path"),
        "eligible_trade_events": 0,
        "issuer_original_published_at_verified": False,
        "production_signal": False,
        "retention_iam_gate": "NOT_VERIFIED",
        "positive_expectancy_verified": False,
    }


def summary_markdown(report):
    return "\n".join([
        "## Sky GCS 研究證據健康報告",
        f"- 雲端資料核驗：**{report['status']}**",
        f"- 已完成快照批次：**{report['source_batches']}**（不是獨立交易日）",
        f"- 暫定唯一事件：**{report['unique_provisional_events']}**（不是合格交易樣本）",
        f"- 重複不變事件：{report['unchanged']}",
        f"- 內容修訂事件：{report['revision']}",
        f"- 無效事件：{report['skipped_invalid']}",
        f"- 原始資料：`{report['gcs_raw_prefix']}`",
        f"- 累積帳本：`{report['gcs_ledger_path']}`",
        "- 原始公告時間：**未驗證**；交易合格事件：**0**",
        "- 保留政策／IAM最小權限：**未驗證**",
        "- 策略正期望：**未證實**；Production：**未變更**",
    ]) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", default="")
    args = ap.parse_args()
    raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    result = safe_health(raw, ledger)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md = summary_markdown(result)
    if args.summary:
        with Path(args.summary).open("a", encoding="utf-8") as fp:
            fp.write(md)
    print(md)


if __name__ == "__main__":
    main()
