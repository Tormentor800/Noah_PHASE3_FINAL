# src/serve/explain.py
import numpy as np
import pandas as pd

# Visible marker so we know THIS file actually loaded
print(">>> using NEW explain.py with SHAP background <<<")

from src.common.io import load_current_model

# Try SHAP; degrade to fallback on any error
try:
    import shap
    _HAS_SHAP = True
except Exception as _e:
    print(f">>> SHAP import failed, using fallback: {_e}")
    shap = None
    _HAS_SHAP = False

# Keep a stable feature order for your demo model
FEATURE_ORDER = ["feat_a", "feat_b"]

def _to_frame(features: dict) -> pd.DataFrame:
    cols = [c for c in FEATURE_ORDER if c in features]
    if not cols:
        cols = sorted(features.keys())
    row = [float(features[c]) for c in cols]
    return pd.DataFrame([row], columns=cols)

def _fallback_explain(model, X: pd.DataFrame, version: str):
    # Simple absolute value “importance” fallback
    if hasattr(model, "predict_proba"):
        prob = float(model.predict_proba(X)[:, 1][0])
    else:
        pred = model.predict(X)
        prob = float(pred[0]) if np.ndim(pred) else float(pred)
    vals = [float(X.iloc[0][c]) if np.isscalar(X.iloc[0][c]) else 0.0 for c in X.columns]
    top = sorted([(c, v) for c, v in zip(X.columns, vals)], key=lambda t: abs(t[1]), reverse=True)[:8]
    return {"version": version, "base": 0.0, "prob": prob, "top_features": top}

def explain_linear(features: dict):
    """
    SHAP explanations for linear/logistic models with a tiny background set.
    Falls back gracefully if anything fails.
    """
    model, version = load_current_model(with_background=False)
    X = _to_frame(features)

    if not _HAS_SHAP:
        return _fallback_explain(model, X, version)

    try:
        # Two-point background (0s and 1s) – replace with training stats later if you like
        bg0 = np.zeros((1, X.shape[1]), dtype=float)
        bg1 = np.ones((1, X.shape[1]), dtype=float)
        X_bg = pd.DataFrame(np.vstack([bg0, bg1]), columns=X.columns)

        # Some SHAP versions don’t like extra kwargs; keep it minimal
        explainer = shap.LinearExplainer(model, X_bg)

        sv = explainer.shap_values(X)
        # Binary classifiers may return a list [class0, class1]
        if isinstance(sv, (list, tuple)):
            vals = sv[1][0] if len(sv) > 1 else sv[0][0]
        else:
            vals = sv[0]

        base = explainer.expected_value
        if isinstance(base, (list, tuple, np.ndarray)):
            base = float(base[1] if len(base) > 1 else base[0])
        else:
            base = float(base)

        if hasattr(model, "predict_proba"):
            prob = float(model.predict_proba(X)[:, 1][0])
        else:
            pred = model.predict(X)
            prob = float(pred[0]) if np.ndim(pred) else float(pred)

        top = sorted(
            [(f, float(v)) for f, v in zip(X.columns, np.asarray(vals).ravel())],
            key=lambda t: abs(t[1]),
            reverse=True
        )[:8]

        return {"version": version, "base": base, "prob": prob, "top_features": top}

    except Exception as e:
        print(f">>> SHAP explainer failed, falling back: {e}")
        return _fallback_explain(model, X, version)
