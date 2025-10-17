from __future__ import annotations
from typing import Any, Mapping

def get_bool(cfg: Mapping[str, Any], key: str, default: bool = False) -> bool:
    try:
        v = cfg
        for part in key.split('.'):
            v = v[part]
        if isinstance(v, bool): return v
        if isinstance(v, str):  return v.strip().lower() in {'1','true','yes','y','on'}
        return bool(v)
    except Exception:
        return default

def get_float(cfg: Mapping[str, Any], key: str, default: float) -> float:
    try:
        v = cfg
        for part in key.split('.'):
            v = v[part]
        return float(v)
    except Exception:
        return default

def get_int(cfg: Mapping[str, Any], key: str, default: int) -> int:
    try:
        v = cfg
        for part in key.split('.'):
            v = v[part]
        return int(v)
    except Exception:
        return default
