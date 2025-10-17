from __future__ import annotations
from typing import Iterable, Tuple, Dict, Any

from src.risk.types import BetPosition
from src.risk.guards import is_kill_switch_enabled, should_block_by_correlation

def gate_new_bet(cfg: Dict[str, Any],
                 new_bet: BetPosition,
                 open_positions: Iterable[BetPosition]) -> Tuple[bool, Dict[str, Any]]:
    if is_kill_switch_enabled(cfg):
        return False, {"reason": "kill_switch"}

    blocked, meta = should_block_by_correlation(new_bet, open_positions, cfg)
    if blocked:
        return False, meta

    return True, {"reason": "ok"}
