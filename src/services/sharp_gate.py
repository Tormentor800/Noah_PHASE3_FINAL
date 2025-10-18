from __future__ import annotations

def passes_sharp_gate(entry_odds: float, sharp_fair_odds: float, min_edge_pp: float = 1.0):
    """
    Return (allowed: bool, meta: dict) enforcing a minimum edge vs sharp entry in *percentage points*.
    Edge% = (entry_odds - sharp_fair_odds) / sharp_fair_odds * 100

    Example:
      entry=2.02, sharp_fair=2.00 -> edge% = +1.0 -> allowed if min_edge_pp <= 1.0
    """
    if sharp_fair_odds <= 0:
        return False, {"reason": "invalid_sharp_price", "edge_pp": None, "threshold_pp": min_edge_pp}
    edge_pp = ((entry_odds - sharp_fair_odds) / sharp_fair_odds) * 100.0
    allowed = edge_pp >= float(min_edge_pp)
    return allowed, {"reason": "ok" if allowed else "edge_too_small", "edge_pp": round(edge_pp, 4), "threshold_pp": float(min_edge_pp)}
