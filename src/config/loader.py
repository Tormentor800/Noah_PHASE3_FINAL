from __future__ import annotations
import os
import yaml
from typing import Any, Dict

_DEFAULTS: Dict[str, Any] = {
    "risk": {
        "kill_switch": False,
        "max_corr": 0.70,
        "corr_min_series": 5,
    }
}

def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def load_config(path: str = "config.yml") -> Dict[str, Any]:
    cfg = dict(_DEFAULTS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            y = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, y)
    # Optional ENV overrides (e.g., RISK_KILL_SWITCH=true)
    env_override = os.environ.get("RISK_KILL_SWITCH")
    if env_override is not None:
        cfg["risk"]["kill_switch"] = env_override.strip().lower() in {"1","true","yes","y","on"}
    env_corr = os.environ.get("RISK_MAX_CORR")
    if env_corr is not None:
        cfg["risk"]["max_corr"] = float(env_corr)
    env_min = os.environ.get("RISK_CORR_MIN_SERIES")
    if env_min is not None:
        cfg["risk"]["corr_min_series"] = int(env_min)
    return cfg
