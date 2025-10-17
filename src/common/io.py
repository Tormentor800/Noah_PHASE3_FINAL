import os
from pathlib import Path

def load_current_model(version=None, with_background=False):
    MODEL_PATH = os.getenv("MODEL_PATH", r".\artifacts\model.joblib")
    try:
        from joblib import load
        if Path(MODEL_PATH).exists():
            model = load(MODEL_PATH)
            bg = None
            return (model, version or "v1.0.0") if not with_background else (model, bg)
    except Exception:
        pass

    # Fallback dummy model so /predict always works
    class Dummy:
        def predict_proba(self, X):
            import numpy as np
            return np.array([[0.4, 0.6]])
    return Dummy(), (version or "v0.0.1")
