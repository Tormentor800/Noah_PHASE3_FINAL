from __future__ import annotations
import os, json
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.common.io import load_current_model

ART = "artifacts"
os.makedirs(ART, exist_ok=True)

# -----------------------------
# Helpers
# -----------------------------
def _build_background_from_point(features: Dict[str, float], n: int = 128, std: float = 0.08) -> pd.DataFrame:
    cols = list(features.keys())
    rows = []
    for _ in range(n):
        row = {}
        for k in cols:
            v = float(features[k])
            row[k] = float(np.clip(np.random.normal(v, std), 0.0, 1.0))
        rows.append(row)
    return pd.DataFrame(rows)[cols].astype(float)

# -----------------------------
# SHAP snapshot
# -----------------------------
def export_shap_snapshot(features: Dict[str, float], background: Optional[List[Dict[str, float]]] = None) -> str:
    import shap  # local import to avoid global dependency on startup
    model, version = load_current_model(with_background=False)

    cols = list(features.keys())
    x0_df = pd.DataFrame([features], columns=cols).astype(float)  # (1, n_features)

    # Build / normalize background
    if background and len(background) > 0:
        bg_df = pd.DataFrame(background)[cols].astype(float)
    else:
        bg_df = _build_background_from_point(features, n=128, std=0.08)

    # --- Batch-safe probability wrapper for any model ---
    def _proba_fn(X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)

        def predict_one(xrow: np.ndarray) -> np.ndarray:
            xrow = np.asarray(xrow, dtype=float).reshape(1, -1)
            # Use predict_proba when available
            if hasattr(model, "predict_proba"):
                p = model.predict_proba(xrow)
                if p.ndim == 2 and p.shape[1] == 2:
                    return p[0]
                if p.ndim == 1:
                    p1 = float(p[0])
                    return np.array([1.0 - p1, p1], dtype=float)
                if p.ndim == 2 and p.shape[1] == 1:
                    p1 = float(p[0, 0])
                    return np.array([1.0 - p1, p1], dtype=float)
                # Fallback for >2 classes: use first and last as [neg, pos]
                return np.array([float(p[0, 0]), float(p[0, -1])], dtype=float)
            # Fallback: use predict as a proxy prob in [0,1]
            y = model.predict(xrow)
            y = float(np.ravel(y)[0])
            y = max(0.0, min(1.0, y))
            return np.array([1.0 - y, y], dtype=float)

        out = np.vstack([predict_one(row) for row in X])
        if out.ndim == 1:
            out = out.reshape(1, -1)
        if out.shape[1] != 2:
            if out.shape[1] == 1:
                p1 = out[:, 0:1]
                out = np.hstack([1 - p1, p1])
            else:
                out = out[:, :2]
        return out

    # Use a generic, robust SHAP explainer with tabular background
    exp = shap.Explainer(_proba_fn, bg_df, algorithm="permutation")
    res = exp(x0_df)  # SHAP handles pandas

    # Extract values consistently across SHAP versions
    vals = np.array(res.values)
    if vals.ndim == 3:        # (n_samples, n_features, n_outputs)
        shap_values = np.array(vals[0, :, -1], dtype=float)  # positive class
    elif vals.ndim == 2:      # (n_samples, n_features)
        shap_values = np.array(vals[0, :], dtype=float)
    else:                      # (n_features,) etc.
        shap_values = np.array(vals).reshape(-1).astype(float)

    ev = np.array(getattr(res, "base_values", getattr(exp, "expected_value", 0.0)))
    base = float(ev.reshape(-1)[-1]) if ev.size else float(ev)

    # Save CSV + simple bar chart
    rows = [{"feature": f, "shap_value": float(v), "abs": float(abs(v))} for f, v in zip(cols, shap_values)]
    df = pd.DataFrame(rows).sort_values("abs", ascending=False)

    csv_path = os.path.join(ART, "shap_snapshot.csv")
    png_path = os.path.join(ART, "shap_snapshot.png")
    df[["feature", "shap_value"]].to_csv(csv_path, index=False)

    top = df.head(8)
    plt.figure(figsize=(6, 4))
    plt.barh(top["feature"][::-1], top["shap_value"][::-1])
    plt.title(f"SHAP Top Factors (v={version})\nbase={base:.3f}")
    plt.tight_layout()
    plt.savefig(png_path, dpi=150)
    plt.close("all")
    return png_path

# -----------------------------
# LIME snapshot (optional)
# -----------------------------
def export_lime_snapshot(features: Dict[str, float], background: Optional[List[Dict[str, float]]] = None) -> Optional[str]:
    # Make LIME optional and never break the run
    try:
        from lime.lime_tabular import LimeTabularExplainer
    except Exception:
        return None

    try:
        model, version = load_current_model(with_background=False)
        cols = list(features.keys())

        # Background
        if background and len(background) > 0:
            X_bg = pd.DataFrame(background)[cols].astype(float).values
        else:
            X_bg = _build_background_from_point(features, n=256, std=0.08).values

        # One instance
        x0 = np.array([features[c] for c in cols], dtype=float)

        # Batch-safe probability function for LIME
        def predict_fn(X):
            X = np.asarray(X, dtype=float)
            if hasattr(model, "predict_proba"):
                p = model.predict_proba(X)
                # normalize to (n,2)
                if p.ndim == 1:
                    p = p.reshape(-1, 1)
                if p.shape[1] == 1:
                    p1 = p[:, :1]
                    p = np.hstack([1 - p1, p1])
                elif p.shape[1] > 2:
                    p = p[:, [0, -1]]  # pick first/last
                return p.astype(float)
            # fallback: predict -> prob
            y = model.predict(X).reshape(-1, 1)
            y = np.clip(y, 0.0, 1.0)
            return np.hstack([1 - y, y]).astype(float)

        explainer = LimeTabularExplainer(
            X_bg,
            feature_names=cols,
            discretize_continuous=False,   # fewer moving parts
            verbose=False,
            mode="classification",
            random_state=42,
            feature_selection="lasso_path"  # avoids forward-selection pitfalls
        )

        exp = explainer.explain_instance(x0, predict_fn, num_features=min(8, len(cols)))

        png_path = os.path.join(ART, "lime_snapshot.png")
        exp.as_pyplot_figure()
        plt.title(f"LIME Top Factors (v={version})")
        plt.tight_layout()
        plt.savefig(png_path, dpi=150)
        plt.close("all")
        return png_path
    except Exception as e:
        # Don’t fail the job because of LIME
        print(f"[LIME] skipped: {e}")
        return None


# -----------------------------
# CLI
# -----------------------------
def run(features: Optional[Dict[str, float]] = None):
    if features is None:
        features = {"feat_a": 0.7, "feat_b": 1.1}
    with open(os.path.join(ART, "snapshot_features.json"), "w", encoding="utf-8") as f:
        json.dump(features, f, indent=2)
    shap_png = export_shap_snapshot(features)
    lime_png = export_lime_snapshot(features)
    print("Wrote:")
    print(" - artifacts/shap_snapshot.csv")
    print(f" - {shap_png}")
    if lime_png:
        print(f" - {lime_png}")
    else:
        print(" - (LIME skipped — install with `py -m pip install lime`)")

if __name__ == "__main__":
    run()
