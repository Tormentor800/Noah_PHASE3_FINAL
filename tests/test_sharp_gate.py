from __future__ import annotations
from src.services.sharp_gate import passes_sharp_gate

def test_sharp_gate_allows_when_edge_ge_1pp():
    ok, meta = passes_sharp_gate(entry_odds=2.02, sharp_fair_odds=2.00, min_edge_pp=1.0)
    assert ok is True
    assert meta["reason"] == "ok"
    assert round(meta["edge_pp"], 3) >= 1.0

def test_sharp_gate_blocks_when_edge_lt_1pp():
    ok, meta = passes_sharp_gate(entry_odds=2.01, sharp_fair_odds=2.00, min_edge_pp=1.0)
    assert ok is False
    assert meta["reason"] == "edge_too_small"
    assert round(meta["edge_pp"], 3) < 1.0

def test_sharp_gate_handles_invalid_sharp_price():
    ok, meta = passes_sharp_gate(entry_odds=2.00, sharp_fair_odds=0.0, min_edge_pp=1.0)
    assert ok is False
    assert meta["reason"] == "invalid_sharp_price"
