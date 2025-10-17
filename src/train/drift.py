from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats

def _psi_bins(expected: np.ndarray, actual: np.ndarray, bins: int = 10):
    # Create quantile bins on expected, compare actual
    quantiles = np.linspace(0, 1, bins+1)
    cuts = np.quantile(expected, quantiles)
    cuts[0] = -np.inf; cuts[-1] = np.inf
    e_hist, _ = np.histogram(expected, bins=cuts)
    a_hist, _ = np.histogram(actual, bins=cuts)
    e_perc = np.clip(e_hist / max(e_hist.sum(), 1), 1e-6, 1.0)
    a_perc = np.clip(a_hist / max(a_hist.sum(), 1), 1e-6, 1.0)
    return e_perc, a_perc

def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    e_perc, a_perc = _psi_bins(expected, actual, bins)
    return float(np.sum((a_perc - e_perc) * np.log(a_perc / e_perc)))

def ks_pvalue(expected: np.ndarray, actual: np.ndarray) -> float:
    # Two-sample KS test (returns p-value)
    _, p = stats.ks_2samp(expected, actual, alternative="two-sided", method="auto")
    return float(p)

def drift_scan_batch(df_ref: pd.DataFrame, df_new: pd.DataFrame, numeric_cols: list[str]):
    out = []
    for col in numeric_cols:
        try:
            ref = df_ref[col].dropna().values
            new = df_new[col].dropna().values
            if len(ref) < 50 or len(new) < 50:
                continue
            val_psi = psi(ref, new, bins=10)
            val_ks = ks_pvalue(ref, new)
            out.append({"feature": col, "psi": val_psi, "ks_p": val_ks})
        except Exception:
            continue
    return pd.DataFrame(out)
