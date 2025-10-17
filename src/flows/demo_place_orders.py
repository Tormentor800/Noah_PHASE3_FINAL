# src/flows/demo_place_orders.py
from __future__ import annotations
from src.adapters.base import OrderRequest
from src.adapters.pinnacle import PinnacleAdapter
from src.adapters.sbo import SBOAdapter
from src.adapters.isn import ISNAdapter

def main():
    req = OrderRequest(
        league="NBA",
        market="ML",
        selection="HOME",
        fair_prob=0.56,
        sharp_entry_prob=0.54,  # passes 1pp gate
        desired_stake=50,
        client_order_id="demo-ord-001",
        max_slippage_bps=40,
    )

    for A in (PinnacleAdapter, SBOAdapter, ISNAdapter):
        adapter = A()
        res = adapter.place_premarket_order(req)
        print(res)

if __name__ == "__main__":
    main()
