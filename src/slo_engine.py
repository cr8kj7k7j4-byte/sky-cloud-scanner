from __future__ import annotations


DEFAULT_SLOS = {
    "TWSE": {"availability_min":0.995,"latency_ms_max":3000,"freshness_seconds_max":120,"critical":True},
    "TPEX": {"availability_min":0.995,"latency_ms_max":3000,"freshness_seconds_max":120,"critical":True},
    "FUGLE": {"availability_min":0.99,"latency_ms_max":2500,"freshness_seconds_max":30,"critical":False},
    "RISK_ENGINE": {"availability_min":0.999,"latency_ms_max":500,"freshness_seconds_max":30,"critical":True},
    "ALERT_ENGINE": {"availability_min":0.99,"latency_ms_max":5000,"freshness_seconds_max":120,"critical":False},
    "STATE_STORE": {"availability_min":0.999,"latency_ms_max":1000,"freshness_seconds_max":60,"critical":True},
}


def evaluate_slo(metric, slo=None):
    m=dict(metric or {})
    service=str(m.get("service") or "")
    target=dict(slo or DEFAULT_SLOS.get(service,{}))
    if not target:
        raise ValueError(f"no SLO defined for {service}")

    availability=float(m.get("success_rate") if m.get("success_rate") is not None else (1.0 if m.get("available") else 0.0))
    latency=float(m.get("latency_ms") if m.get("latency_ms") is not None else 999999.0)
    freshness=float(m.get("freshness_seconds") if m.get("freshness_seconds") is not None else 999999.0)

    checks={
        "availability": availability >= float(target["availability_min"]),
        "latency": latency <= float(target["latency_ms_max"]),
        "freshness": freshness <= float(target["freshness_seconds_max"]),
    }
    failed=[k for k,v in checks.items() if not v]
    return {
        "service":service,
        "passed":not failed,
        "critical":bool(target.get("critical",False)),
        "checks":checks,
        "failed_checks":failed,
        "observed":{
            "availability":availability,
            "latency_ms":latency,
            "freshness_seconds":freshness,
        },
        "target":target,
    }


def evaluate_platform(metrics, slos=None):
    results=[]
    slos=slos or DEFAULT_SLOS
    for metric in metrics or []:
        service=(metric.service if hasattr(metric,"service") else metric.get("service"))
        results.append(evaluate_slo(
            metric.to_dict() if hasattr(metric,"to_dict") else metric,
            slos.get(service),
        ))

    failures=[x for x in results if not x["passed"]]
    critical=[x for x in failures if x["critical"]]
    if critical:
        mode="LOCKDOWN"
    elif failures:
        mode="OBSERVE_ONLY"
    else:
        mode="NORMAL"

    return {
        "mode":mode,
        "slo_passed":not failures,
        "failed_services":[x["service"] for x in failures],
        "critical_failed_services":[x["service"] for x in critical],
        "new_entries_allowed":mode=="NORMAL",
        "live_activation_allowed":False,
        "results":results,
    }
