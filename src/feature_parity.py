from __future__ import annotations

PARITY_FIELDS = (
    "formula",
    "version",
    "timestamp_semantics",
    "normalization",
    "missing_policy",
)

def compare_feature_contracts(offline: dict, online: dict, *, universe_equal: bool) -> dict:
    mismatches = {}
    names = sorted(set(offline) | set(online))
    for name in names:
        a = offline.get(name)
        b = online.get(name)
        if a is None or b is None:
            mismatches[name] = ["MISSING_OFFLINE" if a is None else "MISSING_ONLINE"]
            continue
        diff = [field for field in PARITY_FIELDS if a.get(field) != b.get(field)]
        if diff:
            mismatches[name] = diff
    if not universe_equal:
        mismatches["__universe__"] = ["UNIVERSE_MISMATCH"]
    return {
        "status": "PASS" if not mismatches else "PARITY_FAIL",
        "mismatches": mismatches,
        "checked_features": names,
    }
