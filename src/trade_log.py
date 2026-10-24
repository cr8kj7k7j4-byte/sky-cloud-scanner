# Legacy compatibility adapter.
# Canonical P0-L implementation lives in src/trade_logger.py.
# Keep this module so historical research scripts remain reproducible.

from .trade_logger import (
    TRADE_LEDGER_SCHEMA_VERSION,
    TradeDecisionRecord,
    build_trade_decision_record,
    append_jsonl,
    attach_outcome,
    build_canonical_ledger_entry,
)

TRADE_LOG_SCHEMA_VERSION = TRADE_LEDGER_SCHEMA_VERSION

__all__ = [
    "TRADE_LOG_SCHEMA_VERSION",
    "TRADE_LEDGER_SCHEMA_VERSION",
    "TradeDecisionRecord",
    "build_trade_decision_record",
    "append_jsonl",
    "attach_outcome",
    "build_canonical_ledger_entry",
]
