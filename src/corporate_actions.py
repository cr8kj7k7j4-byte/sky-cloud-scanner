from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Iterable, Optional

@dataclass(frozen=True)
class CorporateAction:
    symbol: str
    action_type: str
    effective_date: str
    source: str
    source_as_of: str
    old_symbol: Optional[str] = None
    new_symbol: Optional[str] = None
    ratio: Optional[float] = None
    cash_amount: Optional[float] = None
    notes: str = ""

    def to_dict(self):
        return asdict(self)

def validate_actions(actions: Iterable[CorporateAction]):
    rows=list(actions or [])
    errors=[]
    keys=set()
    for i,a in enumerate(rows):
        if not a.symbol or not a.action_type or not a.source or not a.source_as_of:
            errors.append(f"missing_required:{i}")
        try:
            date.fromisoformat(a.effective_date)
        except Exception:
            errors.append(f"invalid_effective_date:{i}")
        k=(a.symbol,a.action_type,a.effective_date,a.old_symbol,a.new_symbol)
        if k in keys:
            errors.append(f"duplicate_action:{i}")
        keys.add(k)
        if a.action_type=="SYMBOL_CHANGE" and (not a.old_symbol or not a.new_symbol):
            errors.append(f"symbol_change_missing_mapping:{i}")
        if a.ratio is not None and a.ratio <= 0:
            errors.append(f"invalid_ratio:{i}")
    return {"valid":not errors,"errors":errors,"rows":len(rows)}

def resolve_symbol(symbol: str, as_of: str, actions: Iterable[CorporateAction]):
    current=str(symbol)
    for a in sorted(actions or [], key=lambda x:x.effective_date):
        if a.action_type!="SYMBOL_CHANGE" or a.effective_date > as_of:
            continue
        if current == a.old_symbol and a.new_symbol:
            current=a.new_symbol
    return current

def continuity_chain(symbol: str, actions: Iterable[CorporateAction]):
    chain=[str(symbol)]
    current=str(symbol)
    for a in sorted(actions or [], key=lambda x:x.effective_date):
        if a.action_type=="SYMBOL_CHANGE" and a.old_symbol==current and a.new_symbol:
            current=a.new_symbol
            chain.append(current)
    return chain
