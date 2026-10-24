from __future__ import annotations
import argparse, json
from pathlib import Path


def _load(path):
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--walk-forward", default="research_output/walk_forward.json")
    ap.add_argument("--cost-stress", default="research_output/cost_stress.json")
    ap.add_argument("--leakage-audit", default="research_output/leakage_audit.json")
    ap.add_argument("--out", default="research_output/ml_validation_gate.json")
    args = ap.parse_args()

    wf = _load(args.walk_forward)
    cost = _load(args.cost_stress)
    leakage = _load(args.leakage_audit)

    wf_pass = False
    if wf:
        summaries = [x.get("summary", {}) for x in wf.get("models", {}).values()]
        wf_pass = bool(summaries and all(s.get("passed") for s in summaries))

    cost_pass = bool(cost and cost.get("passed"))

    report = {
        "walk_forward_passed": wf_pass,
        "oos_passed": False,
        "cost_stress_passed": cost_pass,
        "leakage_check_passed": bool(leakage and leakage.get("passed")),
        "paper_trade_passed": False,
    }
    report["production_eligible"] = all(report.values())
    report["status"] = "PRODUCTION_ELIGIBLE" if report["production_eligible"] else "RESEARCH_ONLY"
    report["note"] = (
        "Leakage audit certifies only the dataset contract and obvious leakage checks. "
        "Independent OOS, code review, purging/embargo design and paper trading remain required."
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
