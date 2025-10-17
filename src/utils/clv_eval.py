import numpy as np
import pandas as pd

def implied_prob_from_decimal(decimal_odds: float) -> float:
    if decimal_odds is None:
        return np.nan
    try:
        x = float(decimal_odds)
    except Exception:
        return np.nan
    if x <= 1.0:
        return np.nan
    return 1.0 / x

def choose_closing_prob(row: pd.Series) -> float:
    sel = str(row.get("selection", "")).lower()
    if sel in ("home", "1", "h"):
        return row.get("close_home_prob", np.nan)
    if sel in ("away", "2", "a"):
        return row.get("close_away_prob", np.nan)
    if sel in ("draw", "x", "d"):
        return row.get("close_draw_prob", np.nan)
    return np.nan

def compute_clv(df: pd.DataFrame, model_prob_col: str = "model_prob") -> pd.DataFrame:
    out = df.copy()
    # If model odds are provided, convert to probs
    if model_prob_col not in out.columns and "model_odds" in out.columns:
        out["model_prob"] = 1.0 / out["model_odds"].astype(float)
        model_prob_col = "model_prob"

    # Closing implied probs
    for side in ["home", "draw", "away"]:
        odds_col = f"close_{side}"
        prob_col = f"close_{side}_prob"
        if odds_col in out.columns:
            out[prob_col] = out[odds_col].apply(implied_prob_from_decimal)

    # Selected closing prob
    out["closing_prob_selected"] = out.apply(choose_closing_prob, axis=1)

    # CLV: ratio-based
    out["clv_ratio"] = out[model_prob_col] / out["closing_prob_selected"]
    out["clv"] = out["clv_ratio"] - 1.0

    return out
