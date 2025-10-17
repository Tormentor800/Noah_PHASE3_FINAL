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
