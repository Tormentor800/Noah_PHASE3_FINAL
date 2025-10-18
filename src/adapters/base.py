from dataclasses import dataclass
import os, json

# Default path; tests monkeypatch this to a temp file
IDEMP_PATH = os.path.join("artifacts", "executions_index.jsonl")

def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def load_idempotent(client_order_id: str):
    """Return stored record for client_order_id or None."""
    path = IDEMP_PATH
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: 
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("client_order_id") == client_order_id:
                    return rec
    except Exception:
        return None
    return None

def save_idempotent(record: dict):
    """Append record to JSONL for idempotency; must be EXACT dict to be returned later."""
    path = IDEMP_PATH
    _ensure_dir(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
@dataclass
class OrderRequest:
    league: str
    market: str
    selection: str
    fair_prob: float
    sharp_entry_prob: float
    desired_stake: float
    client_order_id: str
    max_slippage_bps: float

