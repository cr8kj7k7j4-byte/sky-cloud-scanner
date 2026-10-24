from __future__ import annotations
import argparse, json
from pathlib import Path

import pandas as pd


FEATURE_COLS = [
    "ret_1",
    "ret_3",
    "ret_5",
    "vol_5",
    "vol_20",
    "volume_ratio_5",
    "range_pct",
    "close_vs_avg_pct",
]


def _load_symbol(path: Path, horizon_bars: int):
    obj = json.loads(path.read_text(encoding="utf-8"))
    symbol = obj["symbol"]
    rows = obj.get("data", [])
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    needed = {"date", "open", "high", "low", "close", "volume"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}: missing columns {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.sort_values("date").drop_duplicates("date").reset_index(drop=True)

    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if "average" in df.columns:
        df["average"] = pd.to_numeric(df["average"], errors="coerce")
    else:
        df["average"] = pd.NA

    df["ret_1"] = df["close"].pct_change(1) * 100
    df["ret_3"] = df["close"].pct_change(3) * 100
    df["ret_5"] = df["close"].pct_change(5) * 100
    df["vol_5"] = df["close"].pct_change().rolling(5).std() * 100
    df["vol_20"] = df["close"].pct_change().rolling(20).std() * 100

    vol_ma5 = df["volume"].rolling(5).mean().shift(1)
    df["volume_ratio_5"] = df["volume"] / vol_ma5
    df["range_pct"] = (df["high"] - df["low"]) / df["close"] * 100
    df["close_vs_avg_pct"] = (df["close"] / df["average"] - 1) * 100

    # Forward labels. shift(-horizon) is used only for labels, never features.
    future_close = df["close"].shift(-horizon_bars)
    future_high = df["high"].shift(-1).rolling(horizon_bars).max().shift(-(horizon_bars - 1))
    future_low = df["low"].shift(-1).rolling(horizon_bars).min().shift(-(horizon_bars - 1))
    df["target_return_pct"] = (future_close / df["close"] - 1) * 100
    df["target_mfe_pct"] = (future_high / df["close"] - 1) * 100
    df["target_mae_pct"] = (future_low / df["close"] - 1) * 100

    df["symbol"] = symbol
    cols = ["symbol", "date"] + FEATURE_COLS + [
        "target_return_pct", "target_mfe_pct", "target_mae_pct"
    ]
    return df[cols].dropna().reset_index(drop=True)


def build_dataset(data_dir: str, horizon_bars: int):
    frames = []
    for path in sorted(Path(data_dir).glob("*_5.json")):
        if path.name.startswith("_"):
            continue
        frame = _load_symbol(path, horizon_bars)
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["symbol", "date"] + FEATURE_COLS)
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values(["date", "symbol"]).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="research_data")
    ap.add_argument("--out", default="research_output/ml_dataset.parquet")
    ap.add_argument("--horizon-bars", type=int, default=12, help="12 x 5m = 60m")
    args = ap.parse_args()

    df = build_dataset(args.data_dir, args.horizon_bars)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix == ".csv":
        df.to_csv(out, index=False, encoding="utf-8-sig")
    else:
        try:
            df.to_parquet(out, index=False)
        except ImportError:
            out = out.with_suffix(".csv")
            df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"rows={len(df)} symbols={df['symbol'].nunique() if len(df) else 0} out={out}")


if __name__ == "__main__":
    main()
