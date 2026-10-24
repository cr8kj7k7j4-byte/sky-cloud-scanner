import json
import tempfile
from pathlib import Path

from research.build_ml_dataset import build_dataset
from research.train_ml_models import time_split


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rows = []
        # 40 days x 8 bars provides enough timestamps for split validation.
        for d in range(40):
            for i in range(8):
                px = 50 + d * 0.1 + i * 0.02
                rows.append({
                    "date": f"2026-01-{(d % 28)+1:02d}T09:{i*5:02d}:00+08:00",
                    "open": px,
                    "high": px + 0.2,
                    "low": px - 0.2,
                    "close": px + 0.05,
                    "volume": 100 + i * 10,
                    "average": px,
                })
        obj = {"symbol": "TEST", "data": rows}
        (root / "TEST_5.json").write_text(json.dumps(obj), encoding="utf-8")

        df = build_dataset(str(root), horizon_bars=3)
        assert len(df) > 0
        assert "target_return_pct" in df.columns
        assert "target_mfe_pct" in df.columns
        assert "target_mae_pct" in df.columns

        train, val, test = time_split(df)
        assert len(train) > 0 and len(val) > 0 and len(test) > 0
        assert train["date"].max() < val["date"].max() <= test["date"].max()

    print("PASS ML training pipeline smoke tests")


if __name__ == "__main__":
    main()
