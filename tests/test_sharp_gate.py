import os
import pandas as pd
import pytest

PER_BET = os.path.join("artifacts", "per_bet_execution_sharp.csv")
SUMMARY = os.path.join("artifacts", "summary_sharp_entry_vs_clv.csv")

REQUIRED_COLS = {
    "entry_ts", "league", "market",
    "sharp_books_used", "sharp_entry_prob",
    "fair_prob", "edge_vs_sharp_entry",
    "exec_book", "exec_odds", "result"
}

@pytest.mark.order(1)
def test_per_bet_file_exists_and_schema():
    assert os.path.exists(PER_BET), f"Missing {PER_BET} — run: py -m src.flows.sharp_eval_demo"
    df = pd.read_csv(PER_BET)
    missing = REQUIRED_COLS - set(df.columns)
    assert not missing, f"per_bet schema missing: {missing}"

@pytest.mark.order(2)
def test_gate_is_enforced_min_1pp():
    df = pd.read_csv(PER_BET)
    # only evaluate executed bets (if you log prefilters, filter them out)
    assert (df["edge_vs_sharp_entry"] >= 0.01).all(), (
        "Found bet(s) violating hard gate: edge_vs_sharp_entry < 0.01"
    )

@pytest.mark.order(3)
def test_summary_has_group_breakdowns():
    assert os.path.exists(SUMMARY), f"Missing {SUMMARY} — run: py -m src.flows.sharp_eval_demo"
    s = pd.read_csv(SUMMARY)
    # Should have top-level row and optionally grouped rows
    assert {"n","gate_min","pct_passing_gate","pct_clv_gt_0","avg_clv_pp"}.issubset(s.columns)
