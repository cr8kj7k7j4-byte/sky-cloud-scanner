"""W0 #363: independently validate a downloaded same-run single-stock Artifact.

No Fugle calls, no market certification, no trading approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

PASS = "PASS_ARTIFACT_INTEGRITY_RESEARCH_ONLY"
HOLD = "HOLD_ARTIFACT_INTEGRITY"


def receipt(*, local: Path, downloaded: Path, symbol: str, run_id: str,
            attempt: str, head_sha: str, artifact_id: int, unified: bool) -> dict:
    result = {
        "schema": "SKY_SINGLE_STOCK_SAME_RUN_READBACK_V1",
        "status": HOLD, "run_id": str(run_id),
        "attempt": str(attempt), "head_sha": str(head_sha),
        "artifact_id": artifact_id, "symbol": symbol,
        "production_eligible": False, "automatic_order": False,
        "execution_authorized": False, "source_status": "HOLD",
    }
    if not (re.fullmatch(r"[0-9]{4,6}", symbol)
            and re.fullmatch(r"[0-9]+", str(run_id))
            and re.fullmatch(r"[0-9]+", str(attempt))
            and re.fullmatch(r"[0-9a-f]{40}", str(head_sha))
            and type(artifact_id) is int and artifact_id > 0):
        result["reason"] = "INVALID_RUN_IDENTITY"
        return result
    names = [f"{symbol}-5m-source.json", f"{symbol}-5m-source.md"]
    if unified:
        names += [f"{symbol}.json", f"{symbol}.md"]
    if not unified and not (local / names[0]).is_file():
        names = [f"{symbol}.json", f"{symbol}.md"]
    digests = {}
    try:
        for name in names:
            original = (local / name).read_bytes()
            remote = (downloaded / name).read_bytes()
            if not original or original != remote:
                raise ValueError("SAME_RUN_BYTES_MISMATCH")
            digests[name] = hashlib.sha256(remote).hexdigest()
        obj = json.loads((downloaded / names[0]).read_text(encoding="utf-8"))
        if (not isinstance(obj, dict) or obj.get("symbol") != symbol
                or obj.get("production_eligible") is True
                or obj.get("automatic_order") is True
                or obj.get("execution_authorized") is True):
            raise ValueError("SOURCE_SYMBOL_OR_SAFETY_MISMATCH")
        if unified:
            wrapper = json.loads((downloaded / f"{symbol}.json").read_text(encoding="utf-8"))
            if (wrapper.get("symbol") != symbol
                    or wrapper.get("schema") != "SKY_UNIFIED_SINGLE_STOCK_RESEARCH_V1"
                    or wrapper.get("execution_authorized") is not False
                    or wrapper.get("source_audit") != obj
                    or (wrapper.get("observation") or {}).get("execution_authorized") is not False):
                raise ValueError("UNIFIED_SOURCE_INTEGRITY_MISMATCH")
        result["status"] = PASS
        result["source_status"] = (obj.get("five_minute_status")
                                   or obj.get("status") or "HOLD")
        result["file_sha256"] = digests
        result["file_count"] = len(names)
        # A PASS here ONLY attests to same-run Artifact integrity.
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result["reason"] = type(exc).__name__ + ":" + str(exc)[:120]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", required=True)
    parser.add_argument("--downloaded", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--artifact-id", type=int, required=True)
    parser.add_argument("--unified", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = receipt(local=Path(args.local), downloaded=Path(args.downloaded),
                     symbol=args.symbol, run_id=args.run_id, attempt=args.attempt,
                     head_sha=args.sha, artifact_id=args.artifact_id,
                     unified=args.unified)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("SKY_SINGLE_STOCK_INDEPENDENT_READBACK", result["status"])
    if result["status"] != PASS:
        raise SystemExit("SINGLE_STOCK_READBACK_HOLD")


if __name__ == "__main__":
    main()
