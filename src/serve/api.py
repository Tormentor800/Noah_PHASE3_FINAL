from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import traceback

from src.common.io import load_current_model
from src.common.metrics import recent_kpis, error_rates, feature_flags

class PredictIn(BaseModel):
    league: str = "NBA"
    market: str = "ML"
    features: dict

app = FastAPI(title="M7 API")

@app.post("/predict")
def predict(p: PredictIn):
    # --- Auto-disable guards ---
    flags = feature_flags()
    if flags.get("global_kill") or flags.get(p.league) == "off":
        raise HTTPException(status_code=503, detail="Publishing paused by flag")
    kpi = recent_kpis(days=7)
    if kpi["clv_bps"] < -75 or kpi["ev_pct"] < -1.5:
        raise HTTPException(status_code=503, detail="Auto-disable: KPI breach")
    if error_rates(last_min=30)["api_pct"] > 10:
        raise HTTPException(status_code=503, detail="Auto-disable: elevated errors")

    # --- Predict (pandas-free + error visibility) ---
    try:
        model, version = load_current_model()
        # Build a numeric row from features dict
        cols = list(p.features.keys())
        row = [float(p.features[c]) for c in cols]
        X = np.array([row], dtype=float)

        # Predict probability; fall back to predict if no predict_proba
        if hasattr(model, "predict_proba"):
            prob = float(model.predict_proba(X)[:, 1][0])
        else:
            yhat = model.predict(X)
            prob = float(yhat[0]) if np.ndim(yhat) else float(yhat)

        # Simple fair/edge placeholders
        fair = -100 * prob / (1 - prob) if prob >= 0.5 else 100 * (1 - prob) / prob
        edge_bp = int((fair - -110) if fair < 0 else (fair - 110))
        return {"version": version, "prob": prob, "fair_price": fair, "edge_bp": edge_bp}

    except Exception as e:
        # TEMP: return error details for debugging (remove in prod)
        tb = traceback.format_exc(limit=2)
        raise HTTPException(status_code=500, detail=f"{e.__class__.__name__}: {e} | {tb}")


from src.serve.explain import explain_linear

@app.post("/explain")
def explain(p: PredictIn):
    return explain_linear(p.features)

    
@app.get("/health")
def health():
    return {"ok": True}
# ---- lightweight metrics (no deps; reads existing artifacts) ----
import os, json, pandas as pd

@app.get("/metrics")
def metrics():
    art = "artifacts"
    per_bet = os.path.join(art, "per_bet_execution_sharp.csv")
    settlement = os.path.join(art, "settlement_report.csv")
    summary = os.path.join(art, "settlement_summary.csv")

    def _safe_len(path):
        try:
            return int(pd.read_csv(path).shape[0]) if os.path.exists(path) else 0
        except Exception:
            return 0

    m = {
        "ok": True,
        "per_bet_rows": _safe_len(per_bet),
        "settlement_rows": _safe_len(settlement),
        "summary_rows": _safe_len(summary),
    }
    return m
