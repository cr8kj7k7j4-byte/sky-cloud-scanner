"""Fail-closed audit classification tests; never delete branches."""
import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "research" / "sky_all_branches_retired_ledger_audit.py"
spec = importlib.util.spec_from_file_location("retired_branch_audit", MODULE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_default_branch_protected():
    assert audit.classify_branch("main", 0, [], [], [])[0] == "PROTECT"


def test_unmerged_work_protected():
    assert audit.classify_branch("fix/valuable", 1, [], ["src/paper_trading.py"], [])[0] == "HOLD"


def test_references_protected():
    assert audit.classify_branch("fix/referenced", 0, ["docs/README:1"], ["src/paper_trading.py"], [])[0] == "HOLD"


def test_failed_comparison_protected():
    assert audit.classify_branch("fix/unknown", None, [], ["src/paper_trading.py"], [])[0] == "HOLD"


def test_candidate_not_approved_for_deletion():
    status, reason = audit.classify_branch("fix/old", 0, [], ["src/paper_trading.py"], [])
    assert status == "REVIEW_DELETE_CANDIDATE"
    assert "approval_pending" in reason


def test_no_hit_does_not_authorize_deletion():
    assert audit.classify_branch("fix/old", 0, [], [], [])[0] == "NO_RETIRED_PATH"
