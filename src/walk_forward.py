from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta

WALK_FORWARD_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class WalkForwardFold:
    train_start: str
    train_end: str
    validate_start: str
    validate_end: str
    test_start: str
    test_end: str

    def to_dict(self):
        return asdict(self)


def _d(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v))


def generate_walk_forward_folds(start, end, *, train_days=504, validate_days=126, test_days=126, step_days=126):
    start=_d(start); end=_d(end)
    folds=[]
    cursor=start
    while True:
        train_start=cursor
        train_end=train_start+timedelta(days=train_days-1)
        validate_start=train_end+timedelta(days=1)
        validate_end=validate_start+timedelta(days=validate_days-1)
        test_start=validate_end+timedelta(days=1)
        test_end=test_start+timedelta(days=test_days-1)
        if test_end > end:
            break
        folds.append(WalkForwardFold(
            train_start.isoformat(), train_end.isoformat(),
            validate_start.isoformat(), validate_end.isoformat(),
            test_start.isoformat(), test_end.isoformat(),
        ))
        cursor=cursor+timedelta(days=step_days)
    return folds


def chronological_split(records, *, time_key="observed_at", train_ratio=0.6, validate_ratio=0.2):
    rows=sorted(list(records or []), key=lambda x: str(x.get(time_key) or ""))
    n=len(rows)
    if n == 0:
        return {"train":[],"validate":[],"test":[]}
    t=max(1,int(n*train_ratio))
    v=max(t,min(n,int(n*(train_ratio+validate_ratio))))
    return {"train":rows[:t],"validate":rows[t:v],"test":rows[v:]}


def validate_no_overlap(fold):
    ts=_d(fold.train_start); te=_d(fold.train_end)
    vs=_d(fold.validate_start); ve=_d(fold.validate_end)
    xs=_d(fold.test_start); xe=_d(fold.test_end)
    return ts <= te < vs <= ve < xs <= xe
