from __future__ import annotations
import os, json, time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.config.loader import load_config

from src.adapters import pinnacle as ad_p
from src.adapters import sbo as ad_s
from src.adapters import isn as ad_i

@dataclass
class SourceQuote:
    book: str
    price: float
    ts: Optional[float]

class OddsComposite:
    def __init__(self, cfg: Optional[Dict[str, Any]] = None) -> None:
        self.cfg = cfg or load_config()
        self.weights = self.cfg.get("sharp", {}).get("weights", {"pinnacle":0.5,"sbo":0.3,"isn":0.2})
        self.cadence = int(self.cfg.get("sharp", {}).get("cadence_sec", 30))
        self.stale_after = int(self.cfg.get("sharp", {}).get("stale_after_sec", 90))
        self.norm_scheme = (self.cfg.get("sharp", {}).get("normalization", {}) or {}).get("scheme","proportional")

    def _normalize(self, price: float) -> float:
        # For demo: proportional “fair” = price (no margin data), keep hook for real margin removal
        if self.norm_scheme == "none":
            return price
        return price

    def _fresh(self, q: SourceQuote, now: float) -> bool:
        if q.ts is None:
            return True
        return (now - q.ts) <= self.stale_after

    def fetch_all(self, market: Dict[str, Any]) -> List[SourceQuote]:
        rid = f"{market.get('league','UNK')}::{market.get('market','UNK')}::{int(time.time())}"
        quotes: List[SourceQuote] = []
        for fn in (ad_p.fetch_odds, ad_s.fetch_odds, ad_i.fetch_odds):
            r = fn(market, rid)
            quotes.append(SourceQuote(book=r["book"], price=float(r["price"]), ts=r.get("ts")))
        return quotes

    def compose(self, market: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        quotes = self.fetch_all(market)
        fresh = [q for q in quotes if self._fresh(q, now)]
        if not fresh:
            raise RuntimeError("no fresh sources")
        num = 0.0
        den = 0.0
        used = []
        for q in fresh:
            w = float(self.weights.get(q.book, 0.0))
            if w <= 0:
                continue
            fair = self._normalize(q.price)
            num += w * fair
            den += w
            used.append({"book": q.book, "price": q.price, "fair": fair, "w": w})
        if den <= 0:
            raise RuntimeError("no positive weights for fresh sources")
        composite_fair = num / den
        out = {
            "composite_fair": round(composite_fair, 4),
            "composite_raw": round(composite_fair, 4),  # placeholder until margin is applied
            "sources": used,
            "ts": now,
        }
        # snapshot
        os.makedirs("artifacts/odds_composite", exist_ok=True)
        snap = f"artifacts/odds_composite/{int(now)}.json"
        with open(snap, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        return out
