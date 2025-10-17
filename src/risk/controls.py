# src/risk/controls.py
from __future__ import annotations
import os, json, time, pathlib
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List
import yaml
from datetime import datetime, UTC

ART = "artifacts"
LOGS = "logs"
os.makedirs(ART, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

RISK_CFG = "config/risk.yaml"
LEDGER = os.path.join(ART, "risk_ledger.jsonl")      # records of accepted fills (for caps)
RECENT  = os.path.join(ART, "recent_orders.jsonl")   # light cache for duplicate/correlation
EVENTS  = os.path.join(LOGS, "risk_events.log")

@dataclass(frozen=True)
class OrderKey:
    league: str
    market: str
    selection: str

@dataclass
class Order:
    league: str
    market: str
    selection: str
    stake_usd: float
    client_order_id: str
    ts: float  # epoch seconds

def _now() -> float:
    return time.time()

def _today_key() -> str:
    return datetime.now(UTC).date().isoformat()

def _read_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _append_jsonl(path: str, obj: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")

def _iter_jsonl(path: str):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue

def _log_event(msg: str):
    stamp = datetime.now(UTC).isoformat()
    with open(EVENTS, "a", encoding="utf-8") as f:
        f.write(f"{stamp} {msg}\n")

class RiskEngine:
    def __init__(self, cfg_path: str = RISK_CFG):
        self.cfg_path = cfg_path
        self.cfg = _read_yaml(cfg_path)

    # ---------- Public: check & reserve ----------
    def check_order(self, order: Order) -> Tuple[bool, str]:
        """Returns (ok, reason). If ok=False, reason explains the block."""
        # 0) Kill switch
        if self.cfg.get("kill_switch", False):
            return False, "kill_switch_on"

        # 1) Duplicate guard
        dup_sec = int(self.cfg.get("duplicate_guard", {}).get("window_sec", 0))
        if dup_sec > 0 and self._is_duplicate(order, dup_sec):
            return False, f"duplicate_guard_window_{dup_sec}s"

        # 2) Correlation guard
        corr = self.cfg.get("correlation_guard", {})
        corr_sec = int(corr.get("window_sec", 0))
        group_by = corr.get("group_by", ["league", "market"])
        if corr_sec > 0 and self._is_correlated(order, corr_sec, group_by):
            return False, f"correlation_guard_window_{corr_sec}s"

        # 3) Exposure caps
        ok, reason = self._within_caps(order)
        if not ok:
            return False, reason

        return True, "ok"

    def reserve(self, order: Order) -> None:
        """Record the order into the recent cache (for dup/corr) and ledger (for caps)."""
        rec = {
            "ts": order.ts,
            "league": order.league,
            "market": order.market,
            "selection": order.selection,
            "stake_usd": order.stake_usd,
            "client_order_id": order.client_order_id,
        }
        _append_jsonl(RECENT, rec)

        day_key = _today_key()
        _append_jsonl(LEDGER, {**rec, "day": day_key})

    # ---------- Internals ----------
    def _is_duplicate(self, order: Order, window_sec: int) -> bool:
        cutoff = order.ts - window_sec
        for row in _iter_jsonl(RECENT):
            if row.get("ts", 0) < cutoff:
                continue
            if (row.get("league") == order.league and
                row.get("market") == order.market and
                row.get("selection") == order.selection):
                return True
        return False

    def _is_correlated(self, order: Order, window_sec: int, group_by: List[str]) -> bool:
        cutoff = order.ts - window_sec
        target = {k: getattr(order, k, None) for k in group_by}
        for row in _iter_jsonl(RECENT):
            if row.get("ts", 0) < cutoff:
                continue
            if all(row.get(k) == target.get(k) for k in group_by):
                return True
        return False

    def _within_caps(self, order: Order) -> Tuple[bool, str]:
        day = _today_key()
        total = 0.0
        league_total = 0.0
        for row in _iter_jsonl(LEDGER):
            if row.get("day") != day:
                continue
            total += float(row.get("stake_usd", 0.0))
            if row.get("league") == order.league:
                league_total += float(row.get("stake_usd", 0.0))

        cfg_exp = self.cfg.get("exposure", {})
        daily_cap = float(cfg_exp.get("daily_cap_usd", 0.0))
        per_league = {k: float(v) for k, v in (cfg_exp.get("per_league_cap_usd") or {}).items()}

        if daily_cap and total + order.stake_usd > daily_cap:
            return False, f"daily_cap_exceeded({total:.2f}+{order.stake_usd:.2f}>{daily_cap:.2f})"

        cap_lg = per_league.get(order.league)
        if cap_lg and league_total + order.stake_usd > cap_lg:
            return False, f"league_cap_exceeded[{order.league}]({league_total:.2f}+{order.stake_usd:.2f}>{cap_lg:.2f})"

        return True, "ok"

def check_and_reserve(league: str, market: str, selection: str, stake_usd: float,
                      client_order_id: str) -> Tuple[bool, str]:
    eng = RiskEngine()
    ord = Order(
        league=league, market=market, selection=selection,
        stake_usd=float(stake_usd), client_order_id=client_order_id,
        ts=_now()
    )
    ok, reason = eng.check_order(ord)
    if not ok:
        _log_event(f"BLOCK {client_order_id} {league}/{market}/{selection} {stake_usd}usd reason={reason}")
        return False, reason
    eng.reserve(ord)
    _log_event(f"ALLOW {client_order_id} {league}/{market}/{selection} {stake_usd}usd")
    return True, "ok"
