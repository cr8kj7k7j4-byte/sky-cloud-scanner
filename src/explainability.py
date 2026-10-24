def explain(features, ensemble_result):
    features = features or {}
    items = []

    def add(name, value, direction, note):
        items.append({
            "feature": name,
            "value": value,
            "direction": direction,
            "note": note,
        })

    m5 = features.get("momentum_5")
    if m5 is not None:
        add("5期動能", round(float(m5), 3), "positive" if m5 > 0 else "negative", "近期價格動能")

    vr = features.get("volume_ratio")
    if vr is not None:
        add("量比", round(float(vr), 3), "positive" if vr >= 1.2 else "neutral", "量能相對近期均值")

    rs = features.get("relative_strength")
    if rs is not None:
        add("相對強弱", round(float(rs), 3), "positive" if rs > 0 else "negative", "相對大盤表現")

    vwap = features.get("vwap_distance_pct")
    if vwap is not None:
        direction = "risk" if abs(float(vwap)) >= 3 else "neutral"
        add("距均價", round(float(vwap), 3), direction, "Anti-Chase 參考")

    return {
        "method": "transparent_baseline",
        "production_shap_ready": False,
        "drivers": items,
        "ml_consensus": ensemble_result.get("consensus"),
    }
