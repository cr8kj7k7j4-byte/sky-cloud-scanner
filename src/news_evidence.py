"""Legacy compatibility adapter for P0-K news evidence.

Canonical implementation lives in src.knowledge_engine.
"""

from .knowledge_engine import build_news_evidence_ledger

__all__ = ["build_news_evidence_ledger"]
