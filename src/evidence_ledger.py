"""Legacy compatibility adapter for P0-K candidate evidence.

Canonical implementation lives in src.knowledge_engine.
"""

from .knowledge_engine import build_candidate_structured_ledger


def build_evidence_ledger(candidate, run_time=None):
    return build_candidate_structured_ledger(candidate, run_time)
