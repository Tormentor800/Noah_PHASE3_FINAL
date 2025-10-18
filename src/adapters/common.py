from __future__ import annotations
import time, random
from typing import Dict, Any

class AdapterError(Exception):
    pass

def retry(fn, retries=3, backoff_ms=200):
    last = None
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            last = e
            time.sleep((backoff_ms/1000.0) * (2**i))
    raise AdapterError(str(last) if last else "adapter failed")

def clamp_slippage(odds: float, lower: float, upper: float) -> float:
    return max(lower, min(odds, upper))
def fetch_odds(market: str, request_id: str = ""):
    """
    Minimal deterministic odds fetcher used by tests.
    Returns a dict with a 'price' field; price varies slightly by market string.
    """
    base = 1.95
    # tiny deterministic nudge from market string
    nud = (sum(ord(c) for c in (market or "")) % 7) * 0.001
    return {"price": round(base + nud, 3), "market": market, "request_id": request_id}
