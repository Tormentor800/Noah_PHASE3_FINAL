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
