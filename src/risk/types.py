from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class BetPosition:
    bet_id: str
    ts: datetime
    league: str
    market: str
    team_or_side: str
    stake: float
    odds: float
    group_key: Optional[str] = None
