from __future__ import annotations
import random
from typing import Dict, Any
from .common import retry, clamp_slippage

def fetch_odds(market: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    def go():
        base = float(market.get("base_odds", 1.88))
        raw  = base + (random.random()-0.5)*0.05
        raw  = clamp_slippage(raw, 1.50, 3.50)
        return {"book":"sbo","price":round(raw,3),"ts":market.get("ts")}
    return retry(go)
class SBOAdapter:
    """Compatibility shim. Delegates to fetch_odds()."""
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    def get_odds(self, market, request_id: str = ""):
        return fetch_odds(market, request_id)
