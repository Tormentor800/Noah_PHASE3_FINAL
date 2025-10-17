import glob
from datetime import datetime, timedelta, UTC
import pandas as pd

DATA_DIR = r".\data"  # folder with CSV/Parquet

import numpy as np, shap
from src.common.io import load_current_model


def explain_linear(features: dict):
    model, version = load_current_model(with_background=False)
    X = pd.DataFrame([features])
    explainer = shap.LinearExplainer(model, feature_perturbation="interventional")
    sv = explainer.shap_values(X)  # (n_samples, n_features)
    vals = sv[0]
    top = sorted(
        [(f, float(v)) for f, v in zip(X.columns, vals)],
        key=lambda t: abs(t[1]),
        reverse=True,
    )[:8]
    prob = (
        float(model.predict_proba(X)[:, 1][0])
        if hasattr(model, "predict_proba")
        else float(model.predict(X)[0])
    )
    base = explainer.expected_value
    base = float(base[1] if isinstance(base, (list, np.ndarray)) else base)
    return {"version": version, "base": base, "prob": prob, "top_features": top}


def _demo_df(n=240):
    now = datetime.now(UTC).replace(tzinfo=None)  # tz-naive UTC (fix)
    return pd.DataFrame(
        {
            "ts": [now - timedelta(hours=i) for i in range(n)],
            "feat_a": [(0.013 * i) % 1 for i in range(n)],
            "feat_b": [(0.021 * i) % 1 for i in range(n)],
            "label": [int(i % 2 == 0) for i in range(n)],
        }
    )


def _normalize_ts_naive_utc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Coerce any 'ts' (string/object/tz-aware/tz-naive) to tz-naive UTC.
    """
    ts = pd.to_datetime(df["ts"], errors="coerce", utc=True)
    ts = ts.dt.tz_localize(None)
    df = df.copy()
    df["ts"] = ts
    return df.dropna(subset=["ts"])


def load_data(window_days: int = 30) -> pd.DataFrame:
    files = glob.glob(DATA_DIR + r"\*.parquet") or glob.glob(DATA_DIR + r"\*.csv")

    if not files:
        return _demo_df(n=max(240, int(window_days) * 8))

    frames = []
    for f in files:
        if f.endswith(".parquet"):
            df = pd.read_parquet(f)
        else:
            df = pd.read_csv(f)
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)

    if "ts" not in df.columns:
        raise ValueError("Column 'ts' not found in input files.")

    df = _normalize_ts_naive_utc(df)

    # fixed UTC-safe cutoff
    cutoff = pd.Timestamp.now(tz="UTC").tz_localize(None) - pd.Timedelta(days=int(window_days))

    df = df[df["ts"] >= cutoff]

    keep = [c for c in ["ts", "feat_a", "feat_b", "label"] if c in df.columns]
    return df[keep] if keep else df
