from __future__ import annotations
import os
import pandas as pd

from src.settlement.settle import ART, PER_BET, CLOSES, settle_batch

def _make_dummy_closes():
    df = pd.read_csv(PER_BET) if os.path.exists(PER_BET) else pd.DataFrame()
    if df.empty:
        return
    cols = [c for c in ["entry_ts","league","market","selection"] if c in df.columns]
    dfc = df[cols].copy()
    if "selection" not in dfc.columns:
        dfc["selection"] = "HOME"

    if "exec_prob" in df.columns:
        base = df["exec_prob"].astype(float)
    elif "sharp_entry_prob" in df.columns:
        base = df["sharp_entry_prob"].astype(float)
    else:
        base = pd.Series(0.5, index=df.index, dtype=float)

    nudges = (((df.index % 5) - 2) * 0.001).astype(float)  # -0.002 .. +0.002
    dfc["sharp_close_prob"] = (base + nudges).clip(0.01, 0.99)
    dfc.to_csv(CLOSES, index=False)

def main():
    os.makedirs(ART, exist_ok=True)
    _make_dummy_closes()
    res = settle_batch()
    print(res)

if __name__ == "__main__":
    main()
