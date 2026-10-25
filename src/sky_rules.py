"""Legacy compatibility aliases for historical Sky rule imports.

Canonical owners:
- first_gate / spread_pct -> P0-C decision_engine.py
- screening ranking -> P0-O ranking_engine.py
- enrich -> P0-F feature_engine.py
"""

from .decision_engine import first_gate, spread_pct
from .ranking_engine import screening_rank_score
from .feature_engine import enrich_candidate_context

score_for_ranking = screening_rank_score
enrich = enrich_candidate_context

__all__ = [
    "first_gate",
    "spread_pct",
    "score_for_ranking",
    "enrich",
]
