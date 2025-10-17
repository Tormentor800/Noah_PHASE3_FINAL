# src/common/sharp.py
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple
import numpy as np
import pandas as pd

ART = "artifacts"
os.makedirs(ART, exist_ok=True)

# --------------------------
# Gate / schema
# --------------------------
def passes_sharp_gate(fair_prob: float, sharp_entry_prob: float, gate: float = 0.01) -> bool:
    """Hard rule: fair_prob − sharp_entry_prob ≥ gate (default 1pp)."""
    try:
        return (float(fair_prob) - float(sharp_entry_prob)) >= float(gate)
    except Exception:
        return False

PER_BET_COLS: Tuple[str, ...] = (
    "entry_ts",
    "league",
    "market",
    "sharp_books_used",        # e.g. "PINN,SBO,ISN"
    "sharp_entry_prob",        # composite sharp prob at entry (0..1)
    "sharp_close_prob",        # composite sharp prob at close (0..1) if known
    "fair_prob",               # model fair prob at entry (0..1)
    "edge_vs_sharp_entry",     # fair_prob - sharp_entry_prob (in probability points)
    "exec_book",               # book we executed at (for evidence)
    "exec_odds",
    "result",                  # 1/0 (won/lost) or None if unsettled
)

# --------------------------
# I/O helpers
# --------------------------
def append_per_bet(df: pd.DataFrame, path: str = os.path.join(ART, "per_bet_execution_sharp.csv")) -> str:
    """Append per-bet rows with the required schema. Creates file with header if absent."""
    # ensure columns exist (fill missing with NaN)
    for c in PER_BET_COLS:
        if c not in df.columns:
            df[c] = np.nan
    df = df.loc[:, list(PER_BET_COLS)]

    header = not os.path.exists(path) or os.path.getsize(path) == 0
    df.to_csv(path, mode="a", index=False, header=header)
    return path

# --------------------------
# Summary
# --------------------------
def summarize_per_bet(
    per_bet_path: str = os.path.join(ART, "per_bet_execution_sharp.csv"),
    out_overall: str = os.path.join(ART, "summary_sharp_entry_vs_clv.csv"),
    out_groups: str  = os.path.join(ART, "summary_sharp_entry_vs_clv_by_group.csv"),
    gate_min: float = 0.01,
) -> Tuple[str, str]:
    """
    Build two CSVs:
      - overall summary (single-row + echo of parameters)
      - grouped breakdown by (league, market)
    """
    if not os.path.exists(per_bet_path) or os.path.getsize(per_bet_path) == 0:
        # create empty shells so downstream code doesn't crash
        pd.DataFrame().to_csv(out_overall, index=False)
        pd.DataFrame().to_csv(out_groups, index=False)
        return out_overall, out_groups

    df = pd.read_csv(per_bet_path)

    # computed fields
    df["edge_vs_sharp_entry"] = df["fair_prob"].astype(float) - df["sharp_entry_prob"].astype(float)
    # CLV = improvement in sharp prob from entry to close (in percentage points)
    # Positive CLV means the sharp composite moved toward our side.
    df["clv_pp"] = (df["sharp_close_prob"].astype(float) - df["sharp_entry_prob"].astype(float)) * 100.0
    df["pass_gate"] = df["edge_vs_sharp_entry"] >= float(gate_min)
    df["clv_gt_0"] = df["clv_pp"] > 0.0

    # Overall
    overall = pd.DataFrame([{
        "n": int(len(df)),
        "gate_min": float(gate_min),
        "pct_passing_gate": float(df["pass_gate"].mean()) if len(df) else 0.0,
        "pct_clv_gt_0":      float(df["clv_gt_0"].mean()) if len(df) else 0.0,
        "avg_clv_pp":        float(df["clv_pp"].mean())   if len(df) else 0.0,
        "avg_slippage_bps":  float(df.get("slippage_bps", pd.Series(dtype=float)).mean()) if "slippage_bps" in df else np.nan,
        "avg_latency_ms":    float(df.get("latency_ms",   pd.Series(dtype=float)).mean()) if "latency_ms"   in df else np.nan,
    }])

    # Grouped by league/market
    # If league/market are missing in input, create placeholders so the file still renders.
    if "league" not in df.columns:
        df["league"] = "UNK"
    if "market" not in df.columns:
        df["market"] = "UNK"

    grp = (
        df.groupby(["league", "market"], dropna=False)
          .agg(
              n=("edge_vs_sharp_entry", "size"),
              pct_passing_gate=("pass_gate", "mean"),
              pct_clv_gt_0=("clv_gt_0", "mean"),
              avg_clv_pp=("clv_pp", "mean"),
          )
          .reset_index()
    )
    # Make % values human-friendly (still decimals 0..1 in CSV unless you prefer *100)
    overall.to_csv(out_overall, index=False)
    grp.to_csv(out_groups, index=False)
    return out_overall, out_groups
