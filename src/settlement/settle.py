from __future__ import annotations
import os, json
from typing import Dict
import numpy as np
import pandas as pd

ART = "artifacts"
os.makedirs(ART, exist_ok=True)

# Inputs
PER_BET = os.path.join(ART, "per_bet_execution_sharp.csv")
CLOSES  = os.path.join(ART, "sharp_closes.csv")

# Outputs
OUT_CSV = os.path.join(ART, "settlement_report.csv")
SUMMARY = os.path.join(ART, "settlement_summary.csv")
LEDGER  = os.path.join(ART, "ledger_balances.json")

def _safe_read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="utf-8", errors="ignore")

def _ensure_selection(df: pd.DataFrame) -> pd.DataFrame:
    if "selection" not in df.columns:
        df = df.copy()
        df["selection"] = "HOME"
    return df

def settle_batch() -> Dict[str, object]:
    per_bet = _safe_read_csv(PER_BET)
    if per_bet.empty:
        return {"ok": False, "reason": "no per_bet_execution_sharp.csv"}

    closes = _safe_read_csv(CLOSES)  # may be empty

    per_bet = _ensure_selection(per_bet)
    if not closes.empty:
        closes = _ensure_selection(closes)

    merge_keys = [c for c in ["entry_ts","league","market","selection"] if c in per_bet.columns and (closes.empty or c in closes.columns)]
    if not closes.empty and merge_keys:
        df = per_bet.merge(closes, on=merge_keys, how="left", suffixes=("", "_close"))
    else:
        df = per_bet.copy()

    if "sharp_close_prob" in df.columns and "exec_prob" in df.columns:
        df["clv_pp"] = (df["sharp_close_prob"] - df["exec_prob"]) * 100.0
    else:
        df["clv_pp"] = np.nan

    if "result" in df.columns and "stake" in df.columns:
        df["pnl"] = np.where(df["result"].astype(float) > 0.5, df["stake"].astype(float), -df["stake"].astype(float))
    else:
        df["pnl"] = np.nan

        # Normalize expected columns for tests/consumers
    if "sharp_close_prob" not in df.columns and "sharp_close_prob_close" in df.columns:
        df["sharp_close_prob"] = df["sharp_close_prob_close"]
    if "stake" not in df.columns:
        # default unknown stake to 0.0 to satisfy schema
        df["stake"] = 0.0

    df.to_csv(OUT_CSV, index=False)

    rows = []
    tot = len(df)
    pct_clv_pos = float((df["clv_pp"] > 0).mean()) if tot else 0.0
    rows.append({"scope":"overall","n":tot,"pct_clv_gt_0":pct_clv_pos,"avg_clv_pp":float(df["clv_pp"].mean())})

    if "league" in df.columns:
        g = df.groupby("league", dropna=False)["clv_pp"]
        for k, s in g:
            rows.append({"scope":f"league={k}","n":int(s.shape[0]),"pct_clv_gt_0":float((s>0).mean()),"avg_clv_pp":float(s.mean())})
    if "market" in df.columns:
        g = df.groupby("market", dropna=False)["clv_pp"]
        for k, s in g:
            rows.append({"scope":f"market={k}","n":int(s.shape[0]),"pct_clv_gt_0":float((s>0).mean()),"avg_clv_pp":float(s.mean())})

    pd.DataFrame(rows).to_csv(SUMMARY, index=False)

    ledger = {"balances": {"house": float(df["pnl"].fillna(0).sum())}}
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)

    return {"ok": True, "wrote": {"report": OUT_CSV, "summary": SUMMARY, "ledger": LEDGER}}
