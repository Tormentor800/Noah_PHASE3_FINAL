from __future__ import annotations
from src.settlement.settle import Bet, compute_clv, settle_one, reconcile_ledger, export_edge_vs_close_csv
import os

def test_compute_clv_basic():
    assert round(compute_clv(2.00, 2.20), 4) == 10.0     # +10%
    assert round(compute_clv(2.00, 1.80), 4) == -10.0    # -10%

def test_settle_one_win_loss_push(tmp_path):
    b_win = Bet("b1","NBA","Spread","LAL -3.5", 100, 1.95, 1.90, "win")
    pnl_win, row_win = settle_one(b_win)
    assert round(pnl_win,2) == 95.0
    assert row_win["clv_pct"] == round((1.90-1.95)/1.95*100,3)

    b_loss = Bet("b2","NBA","Spread","BOS +3.5", 100, 1.90, 1.92, "loss")
    pnl_loss, row_loss = settle_one(b_loss)
    assert round(pnl_loss,2) == -100.0

    b_push = Bet("b3","NBA","Total","UNDER 215.5", 50, 1.85, 1.83, "push")
    pnl_push, row_push = settle_one(b_push)
    assert pnl_push == 0.0

def test_reconcile_and_export(tmp_path):
    bets = [
        Bet("b1","EPL","ML","Arsenal",   100, 2.10, 2.05, "win"),
        Bet("b2","EPL","ML","Chelsea",    80, 1.80, 1.85, "loss"),
        Bet("b3","EPL","Total","Over 2.5",50, 2.00, 1.95, "push"),
    ]
    total, rows = reconcile_ledger(bets)
    # b1 win: +110, b2 loss: -80, b3 push: 0  => total +30
    assert round(total,2) == 30.0
    assert len(rows) == 3

    outp = os.path.join("artifacts","settlement","summary_edge_vs_close.csv")
    export_edge_vs_close_csv(rows, outp)
    assert os.path.exists(outp)
    with open(outp, "r", encoding="utf-8") as f:
        head = f.readline().strip().split(",")
    assert head[:4] == ["bet_id","league","market","team_or_side"]
