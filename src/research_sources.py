from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from .knowledge_engine import Evidence


@dataclass(frozen=True)
class ResearchSource:
    key: str
    name: str
    source_type: str
    authority_rank: int
    supports: tuple

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "source_type": self.source_type,
            "authority_rank": self.authority_rank,
            "supports": list(self.supports),
        }


SOURCE_REGISTRY = {
    "mops": ResearchSource(
        key="mops",
        name="公開資訊觀測站 MOPS",
        source_type="official",
        authority_rank=100,
        supports=("material_event", "financial", "investor_conference"),
    ),
    "twse": ResearchSource(
        key="twse",
        name="臺灣證券交易所 TWSE",
        source_type="exchange",
        authority_rank=95,
        supports=("market", "listing", "trading_notice"),
    ),
    "tpex": ResearchSource(
        key="tpex",
        name="證券櫃檯買賣中心 TPEx",
        source_type="exchange",
        authority_rank=95,
        supports=("market", "listing", "trading_notice"),
    ),
    "company": ResearchSource(
        key="company",
        name="公司官方投資人關係資料",
        source_type="company",
        authority_rank=90,
        supports=("financial", "investor_conference", "operations"),
    ),
    "media": ResearchSource(
        key="media",
        name="可信媒體",
        source_type="media",
        authority_rank=65,
        supports=("news", "industry", "policy"),
    ),
}


def get_source(key: str) -> ResearchSource:
    if key not in SOURCE_REGISTRY:
        raise KeyError(f"unknown research source: {key}")
    return SOURCE_REGISTRY[key]


def normalize_record(
    *,
    symbol: str,
    category: str,
    statement: str,
    source_key: str,
    source_url: Optional[str] = None,
    published_at: Optional[str] = None,
    observed_at: Optional[str] = None,
    confidence: float = 1.0,
    status: str = "FACT",
) -> Evidence:
    src = get_source(source_key)
    return Evidence(
        symbol=str(symbol),
        category=str(category),
        statement=str(statement).strip(),
        source_type=src.source_type,
        source_name=src.name,
        source_url=source_url,
        published_at=published_at,
        observed_at=observed_at,
        confidence=max(0.0, min(1.0, float(confidence))),
        status=status,
    )


def normalize_many(records: Iterable[Dict[str, Any]]) -> List[Evidence]:
    out: List[Evidence] = []
    for row in records:
        out.append(normalize_record(**row))
    return out


def source_health_template() -> Dict[str, Any]:
    return {
        key: {
            "name": src.name,
            "authority_rank": src.authority_rank,
            "supports": list(src.supports),
            "status": "NOT_CONNECTED",
            "last_success_at": None,
            "last_error": None,
        }
        for key, src in SOURCE_REGISTRY.items()
    }


def classify_event(text: str) -> Dict[str, Any]:
    t = (text or "").lower()
    mapping = [
        ("financial", ("營收", "eps", "毛利", "財報", "獲利", "虧損")),
        ("investor_conference", ("法說", "investor", "conference")),
        ("operations", ("產能", "出貨", "接單", "資本支出", "capex")),
        ("risk", ("停工", "訴訟", "裁罰", "下修", "違約", "召回")),
        ("growth", ("新產品", "新客戶", "擴產", "量產", "切入")),
        ("policy", ("政策", "法規", "關稅", "補助")),
        ("industry", ("產業", "供應鏈", "需求", "庫存")),
    ]
    hits = [name for name, words in mapping if any(w in t for w in words)]
    return {
        "primary": hits[0] if hits else "other",
        "tags": hits,
        "trade_signal": False,
    }
