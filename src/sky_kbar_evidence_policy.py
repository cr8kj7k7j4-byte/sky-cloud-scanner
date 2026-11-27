"""W0 #363: canonical K-bar evidence classification for Sky research consumers.

No K-bar minimum is required to publish a dated observation report.
This pure function never certifies full-session coverage, PIT, VWAP or trades.
"""
from __future__ import annotations

NO_BARS = "OBSERVATION_ONLY_NO_5M_BARS"
SPARSE = "OBSERVATION_ONLY_SPARSE_5M_BARS"
OBSERVED = "OBSERVATION_ONLY_5M_BARS_OBSERVED"
INVALID = "HOLD_INVALID_5M_SOURCE"


def classify(*, source_valid: bool, observed_bars: int, missing_slots: int | None = None) -> dict:
    """Separate report availability from K-bar-dependent evidence.

    A missing minute may simply have no executed trades. It is not evidence
    that a trade occurred, and is not by itself a reason to block research.
    Corrupt source identity, timestamps or bars remain invalid.
    """
    if type(source_valid) is not bool or type(observed_bars) is not int or observed_bars < 0:
        raise ValueError("INVALID_KBAR_EVIDENCE_ARGUMENTS")
    if missing_slots is not None and (type(missing_slots) is not int or missing_slots < 0):
        raise ValueError("INVALID_KBAR_MISSING_SLOTS")
    level = (
        INVALID if not source_valid else NO_BARS if observed_bars == 0
        else SPARSE if missing_slots else OBSERVED
    )
    return {
        "kbar_evidence_level": level,
        "research_report_available": source_valid,
        "five_minute_indicators_available": source_valid and observed_bars > 0,
        "observed_5m_bar_count": observed_bars,
        "missing_5m_slots_observed": missing_slots,
        "session_coverage_certified": False,
        "independent_vwap_certified": False,
        "execution_authorized": False,
        "production_eligible": False,
    }
