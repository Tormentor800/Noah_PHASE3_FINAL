from __future__ import annotations
import random
from typing import Dict, Any
from .common import retry, clamp_slippage

def fetch_odds(market: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Return raw decimal odds; stubbed offline with tiny jitter."""
    def go():
        base = float(market.get("base_odds", 1.90))
        raw  = base + (random.random()-0.5)*0.04
        raw  = clamp_slippage(raw, 1.50, 3.50)
        return {"book":"pinnacle","price":round(raw,3),"ts":market.get("ts")}
    return retry(go)
class PinnacleAdapter:
    """Compatibility shim for older tests. Delegates to fetch_odds()."""
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    def get_odds(self, market, request_id: str = ""):
        return fetch_odds(market, request_id)
