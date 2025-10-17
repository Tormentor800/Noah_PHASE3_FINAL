from __future__ import annotations
import os, json, time
from dataclasses import dataclass
from typing import Optional, Dict, Any
import numpy as np

IDEMP_PATH = os.environ.get("IDEMP_INDEX", "artifacts/executions_index.jsonl")
os.makedirs(os.path.dirname(IDEMP_PATH), exist_ok=True)

def _load_yaml(path: str) -> dict:
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

@dataclass
class OrderRequest:
    league: str
    market: str
    selection: str
    fair_prob: float
    sharp_entry_prob: float
    desired_stake: float
    client_order_id: str
    max_slippage_bps: int = 40
    entry_prob: Optional[float] = None

class BaseAdapter:
    NAME = "base"
    FEE_BPS = 8

    def __init__(self, cfg_path: str = "config/brokers.yaml") -> None:
        self.cfg = _load_yaml(cfg_path).get(self.NAME, {})

    def place(self, req: OrderRequest) -> Dict[str, Any]:
        edge = float(req.fair_prob) - float(req.sharp_entry_prob)
        if edge < 0.01:
            raise Exception("Entry gate failed: edge_vs_sharp_entry < 0.01")

        prior = self._read_idempotent(req.client_order_id)
        if prior is not None:
            return prior

        entry_prob = float(req.entry_prob if req.entry_prob is not None else req.sharp_entry_prob)
        slip = np.random.normal(0.0, 0.0003)
        exec_prob = float(np.clip(entry_prob + slip, 0.0001, 0.9999))

        stake = float(req.desired_stake)
        max_bps = int(req.max_slippage_bps)

        def bps(a: float, b: float) -> float:
            return abs(a - b) * 10000.0

        tries = 0
        while bps(exec_prob, entry_prob) > max_bps and tries < 10:
            stake = max(1.0, stake * 0.5)
            slip = np.random.normal(0.0, 0.0002)
            exec_prob = float(np.clip(entry_prob + slip, 0.0001, 0.9999))
            tries += 1

        res = {
            "book": self.NAME,
            "league": req.league,
            "market": req.market,
            "selection": req.selection,
            "client_order_id": req.client_order_id,
            "entry_prob": entry_prob,
            "exec_prob": exec_prob,
            "stake": stake,
            "note": "filled" if stake >= 1.0 else "rejected",
            "fee_bps": self.FEE_BPS,
            "ts": time.time(),
        }
        self._write_idempotent(res)
        return res

    def place_premarket_order(self, req: OrderRequest) -> Dict[str, Any]:
        return self.place(req)

    def _read_idempotent(self, client_order_id: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(IDEMP_PATH):
            return None
        try:
            with open(IDEMP_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    if obj.get("client_order_id") == client_order_id:
                        return obj
        except Exception:
            pass
        return None

    def _write_idempotent(self, record: Dict[str, Any]) -> None:
        try:
            with open(IDEMP_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass
