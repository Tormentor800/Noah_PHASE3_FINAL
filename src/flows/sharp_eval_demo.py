# src/flows/sharp_eval_demo.py
from __future__ import annotations
import os, random
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

from src.common.sharp import (
    passes_sharp_gate,
    append_per_bet,
    summarize_per_bet,
)

ART = "artifacts"
os.makedirs(ART, exist_ok=True)

LEAGUES  = ["NBA", "NHL", "EPL"]
MARKETS  = ["ML", "AH", "OU"]  # Moneyline, Asian Handicap, Over/Under
BOOKS    = "PINN,SBO,ISN"      # AsianConnect composite scope (BIA excluded)

def _rng(n: int = 400, seed: int = 17) -> pd.DataFrame:
    """Generate dummy per-bet evidence with league/market + entry/close sharps."""
    rng = np.random.default_rng(seed)
    now = datetime.now(timezone.utc)

    rows = []
    for i in range(n):
        league = random.choice(LEAGUES)
        market = random.choice(MARKETS)

        sharp_entry_prob = float(np.clip(rng.normal(0.50, 0.05), 0.05, 0.95))
        fair_prob        = float(np.clip(sharp_entry_prob + rng.normal(0.012, 0.010), 0.05, 0.95))  # ~1.2pp edge on avg
        sharp_close_prob = float(np.clip(sharp_entry_prob + rng.normal(0.000, 0.015), 0.05, 0.95))

        edge = fair_prob - sharp_entry_prob
        exec_odds = 1.0 / max(1e-6, sharp_entry_prob)  # dummy decimal odds
        result = rng.integers(0, 2)  # 0/1

        rows.append({
            "entry_ts": (now - timedelta(minutes=i)).isoformat(),
            "league": league,
            "market": market,
            "sharp_books_used": BOOKS,
            "sharp_entry_prob": sharp_entry_prob,
            "sharp_close_prob": sharp_close_prob,
            "fair_prob": fair_prob,
            "edge_vs_sharp_entry": edge,
            "exec_book": "AC",   # AsianConnect brokered
            "exec_odds": exec_odds,
            "result": int(result),
            # optional ops fields
            "slippage_bps": float(rng.normal(0, 15)),      # demo
            "latency_ms":   int(abs(rng.normal(120, 40)))  # demo
        })
    return pd.DataFrame(rows)

def main():
    df = _rng(n=400, seed=17)

    # Enforce the 1% entry gate for logging (what we ship as evidence)
    df = df[df["edge_vs_sharp_entry"] >= 0.01].reset_index(drop=True)

    per_bet_path = append_per_bet(df)
    out_overall, out_groups = summarize_per_bet(per_bet_path)

    # Pretty print to console
    over = pd.read_csv(out_overall)
    print(f"Wrote {os.path.basename(per_bet_path)} and {os.path.basename(out_overall)} (+by_group)")
    print(over.to_string(index=False))

if __name__ == "__main__":
    main()
