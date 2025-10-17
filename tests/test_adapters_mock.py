# tests/test_adapters_mock.py
from __future__ import annotations
import os, json
from src.adapters.base import OrderRequest, IDEMP_PATH
from src.adapters.pinnacle import PinnacleAdapter

def test_idempotency_and_gate(tmp_path, monkeypatch):
    # use a temp artifacts file
    apath = tmp_path / "executions_index.jsonl"
    monkeypatch.setattr("src.adapters.base.IDEMP_PATH", str(apath))

    # gate pass
    req_ok = OrderRequest(
        league="EPL", market="ML", selection="HOME",
        fair_prob=0.55, sharp_entry_prob=0.54, desired_stake=10,
        client_order_id="idemp-1", max_slippage_bps=40
    )
    ad = PinnacleAdapter()
    res1 = ad.place_premarket_order(req_ok)
    assert res1["book"] == "pinnacle"
    # second call must return identical record (idempotent)
    res2 = ad.place_premarket_order(req_ok)
    assert res2 == res1

def test_slippage_autoresize(tmp_path, monkeypatch):
    apath = tmp_path / "executions_index.jsonl"
    monkeypatch.setattr("src.adapters.base.IDEMP_PATH", str(apath))

    # Force a tiny max slippage to trigger auto-resize often
    req = OrderRequest(
        league="NFL", market="ML", selection="HOME",
        fair_prob=0.60, sharp_entry_prob=0.59, desired_stake=100,
        client_order_id="slip-1", max_slippage_bps=1  # 1 bps
    )
    ad = PinnacleAdapter()
    res = ad.place_premarket_order(req)
    assert res["stake"] <= 100
    assert res["stake"] >= 1
    assert "filled" in res["note"] or "auto_resized" in res["note"]

def test_gate_block(tmp_path, monkeypatch):
    apath = tmp_path / "executions_index.jsonl"
    monkeypatch.setattr("src.adapters.base.IDEMP_PATH", str(apath))

    # gate fail (less than 1pp)
    req_bad = OrderRequest(
        league="NBA", market="ML", selection="AWAY",
        fair_prob=0.545, sharp_entry_prob=0.54, desired_stake=10,
        client_order_id="gate-bad", max_slippage_bps=40
    )
    ad = PinnacleAdapter()
    import pytest
    with pytest.raises(Exception):
        ad.place_premarket_order(req_bad)
