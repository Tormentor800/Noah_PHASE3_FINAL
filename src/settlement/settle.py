from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Iterable, Tuple
import csv
import math
import os

@dataclass(frozen=True)
class Bet:
    bet_id: str
    league: str
    market: str
    team_or_side: str
    stake: float            # risked amount (units or currency)
    entry_odds: float       # decimal odds
    close_odds: float       # decimal odds at close (sharp)
    result: str             # "win" | "loss" | "push"

def grade_bet(result: str) -> str:
    r = (result or "").strip().lower()
    if r in {"win","loss","push"}:
        return r
    raise ValueError(f"Unknown result: {result}")

def compute_clv(entry_odds: float, close_odds: float) -> float:
    """CLV % = (close_price - entry_price) / entry_price * 100 (on decimal odds)."""
    if entry_odds <= 1e-12 or math.isnan(entry_odds):
        return 0.0
    return (close_odds - entry_odds) / entry_odds * 100.0

def _payout_decimal(stake: float, odds: float) -> float:
    """Return profit (not return) for decimal odds on win; loss returns -stake; push -> 0."""
    return stake * (odds - 1.0)

def settle_one(b: Bet) -> Tuple[float, Dict[str, Any]]:
    """Return (pnl, row_dict) for CSV/summary."""
    res = grade_bet(b.result)
    if res == "win":
        pnl = _payout_decimal(b.stake, b.entry_odds)
    elif res == "loss":
        pnl = -b.stake
    else:  # push
        pnl = 0.0
    clv_pct = compute_clv(b.entry_odds, b.close_odds)
    row = {
        "bet_id": b.bet_id,
        "league": b.league,
        "market": b.market,
        "team_or_side": b.team_or_side,
        "entry_odds": round(b.entry_odds, 4),
        "close_odds": round(b.close_odds, 4),
        "clv_pct": round(clv_pct, 3),
        "result": res,
        "stake": round(b.stake, 2),
        "pnl": round(pnl, 2),
    }
    return pnl, row

def reconcile_ledger(bets: Iterable[Bet]) -> Tuple[float, List[Dict[str, Any]]]:
    """Compute total pnl and rows suitable for export."""
    total = 0.0
    rows: List[Dict[str, Any]] = []
    for b in bets:
        pnl, row = settle_one(b)
        total += pnl
        rows.append(row)
    return round(total, 2), rows

def export_edge_vs_close_csv(rows: List[Dict[str, Any]], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ["bet_id","league","market","team_or_side","entry_odds","close_odds","clv_pct","result","stake","pnl"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def post_balance_update(total_pnl: float) -> None:
    """
    Stub hook for your internal API: POST /settlement/update_balance { delta: total_pnl }.
    Wire up `requests` here if/when desired. Kept as a no-op to remain unit-testable offline.
    """
    return

# --- Compatibility constants for older tests ---
try: ART
except NameError: ART = os.path.join("artifacts", "settlement")
try: PER_BET
except NameError: PER_BET = os.path.join(ART, "per_bet.csv")
try: CLOSES
except NameError: CLOSES = os.path.join(ART, "closes.csv")
try: OUT_CSV
except NameError: OUT_CSV = os.path.join(ART, "summary_edge_vs_close.csv")
try: SUMMARY
except NameError: SUMMARY = OUT_CSV
# --- Compatibility shim: settle_batch(per_bet_csv, closes_csv, out_csv=None) ---
def settle_batch(per_bet_csv: str, closes_csv: str, out_csv: str | None = None):
    """
    Load per-bet executions and sharp closes, compute CLV%% by row, and write a summary CSV.
    Tries to be forgiving about column names and join keys.

    Returns: output CSV path (str).
    """
    import os
    import pandas as pd

    # Resolve output path
    out_dir = ART if "ART" in globals() else os.path.join("artifacts", "settlement")
    os.makedirs(out_dir, exist_ok=True)
    out_csv = out_csv or (OUT_CSV if "OUT_CSV" in globals() else os.path.join(out_dir, "summary_edge_vs_close.csv"))

    # Load inputs
    bets = pd.read_csv(per_bet_csv)
    closes = pd.read_csv(closes_csv)

    # Normalize column names (lowercase for matching)
    bets.columns   = [c.strip() for c in bets.columns]
    closes.columns = [c.strip() for c in closes.columns]

    # Pick a join key
    join_keys = [k for k in ["bet_id","event_id","id"] if (k in bets.columns and k in closes.columns)]
    if join_keys:
        key = join_keys[0]
        merged = bets.merge(closes, on=key, how="left", suffixes=("", "_close"))
    else:
        # Fallback: positional join on index (left length wins)
        closes = closes.copy()
        closes["__row__"] = range(len(closes))
        bets = bets.copy()
        bets["__row__"] = range(len(bets))
        merged = bets.merge(closes, on="__row__", how="left", suffixes=("", "_close"))
        key = "__row__"

    # Resolve columns for entry and close odds
    def first_col(df, names):
        for n in names:
            if n in df.columns: return n
        return None

    entry_col = first_col(merged, ["entry_odds","price_entry","odds_entry","odds"])
    close_col = first_col(merged, ["sharp_close_odds","close_odds","price_close","odds_close","close"])

    # Compute CLV% robustly
    import numpy as np
    entry = merged[entry_col].astype(float) if entry_col else np.nan
    close = merged[close_col].astype(float) if close_col else np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        clv_pct = (close - entry) / entry * 100.0
    merged["clv_pct"] = np.round(clv_pct.replace([np.inf,-np.inf], np.nan).fillna(0.0), 4)

    # Build compact summary
    keep_cols = []
    for c in [key, entry_col, close_col, "clv_pct"]:
        if c and c in merged.columns and c not in keep_cols:
            keep_cols.append(c)
    summary = merged[keep_cols].copy()
    # Friendly column names
    if entry_col and entry_col != "entry_odds":
        summary = summary.rename(columns={entry_col: "entry_odds"})
    if close_col and close_col != "sharp_close_odds":
        summary = summary.rename(columns={close_col: "sharp_close_odds"})

    summary.to_csv(out_csv, index=False, encoding="utf-8")
    return out_csv
