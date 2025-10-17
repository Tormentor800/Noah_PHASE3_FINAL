from __future__ import annotations
from dataclasses import asdict
from typing import Iterable, Mapping, Any, Dict, Tuple, List
import math
import statistics
from collections import defaultdict

from .types import BetPosition
from .config import get_bool, get_float, get_int


def is_kill_switch_enabled(cfg: Mapping[str, Any]) -> bool:
    """Global blocker. When True, no new bets may be placed."""
    return get_bool(cfg, "risk.kill_switch", False)


def _group_key(b: BetPosition) -> str:
    """Group positions by league+market so correlations are computed within comparable buckets."""
    return b.group_key or f"{b.league}::{b.market}".lower()


def _series_for_corr(positions: Iterable[BetPosition]) -> Dict[str, List[float]]:
    """
    Build stake series keyed by team_or_side, aligned by DISTINCT TIMESTAMPS (time bins).
    Each index represents one timestamp seen in the group; for that index, each side gets
    the SUM of stakes at that timestamp (0.0 if none). This avoids interleaving artifacts.
    """
    by_time: Dict[object, List[BetPosition]] = defaultdict(list)
    sides_set = set()
    for p in positions:
        by_time[p.ts].append(p)
        sides_set.add(p.team_or_side)

    sides = sorted(sides_set)
    times = sorted(by_time.keys())

    # Initialize series
    series: Dict[str, List[float]] = {s: [0.0] * len(times) for s in sides}

    # Fill per time-bin sums
    for idx, t in enumerate(times):
        bucket = by_time[t]
        # sum stakes per side at this exact timestamp
        sums: Dict[str, float] = defaultdict(float)
        for p in bucket:
            sums[p.team_or_side] += p.stake
        for s in sides:
            series[s][idx] = float(sums.get(s, 0.0))

    return series


def _pearson(x: List[float], y: List[float]) -> float:
    """Robust Pearson correlation. Returns 0.0 on degenerate vectors or NaN."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    x = x[-n:]
    y = y[-n:]
    if all(v == 0 for v in x) or all(v == 0 for v in y):
        return 0.0
    try:
        mx = statistics.fmean(x)
        my = statistics.fmean(y)
        num = sum((a - mx) * (b - my) for a, b in zip(x, y))
        dx = math.sqrt(sum((a - mx) ** 2 for a in x))
        dy = math.sqrt(sum((b - my) ** 2 for b in y))
        if dx == 0 or dy == 0:
            return 0.0
        val = num / (dx * dy)
        if val != val:  # NaN
            return 0.0
        if val > 1.0:
            val = 1.0
        elif val < -1.0:
            val = -1.0
        return val
    except Exception:
        return 0.0


def should_block_by_correlation(
    new_bet: BetPosition,
    open_positions: Iterable[BetPosition],
    cfg: Mapping[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    """Block if historical OR post-append positive correlation > threshold within the group."""
    max_corr = get_float(cfg, "risk.max_corr", 0.7)
    min_series = get_int(cfg, "risk.corr_min_series", 5)
    eps = 1e-9

    group = _group_key(new_bet)
    relevant = [p for p in open_positions if _group_key(p) == group]

    # Not enough data to judge correlation → allow
    if len(relevant) < max(2, min_series - 1):
        return False, {"reason": "insufficient_series", "group": group, "observations": len(relevant)}

    # Build aligned historical series (binned by timestamp)
    hist_series = _series_for_corr(relevant)
    candidate_key = new_bet.team_or_side
    offenders: List[Tuple[str, float]] = []

    if candidate_key in hist_series:
        cand_hist = hist_series[candidate_key]
        for other_side, vec in hist_series.items():
            if other_side == candidate_key:
                continue
            corr = _pearson(cand_hist, vec)
            if (corr is not None) and (corr > 0.0 + eps) and (corr > max_corr + eps):
                offenders.append((other_side, corr))
        if offenders:
            offenders.sort(key=lambda t: t[1], reverse=True)
            return True, {
                "reason": "high_correlation",
                "group": group,
                "threshold": max_corr,
                "offenders": offenders[:5],
                "new_bet": asdict(new_bet),
            }

    # If historical did not block, simulate appending the new bet at its timestamp
    # Append the new bet to relevant and rebuild (keeps alignment by distinct timestamps)
    simulated = list(relevant) + [new_bet]
    post_series = _series_for_corr(simulated)
    cand_post = post_series.get(candidate_key, [])

    offenders = []
    for other_side, vec in post_series.items():
        if other_side == candidate_key:
            continue
        corr = _pearson(cand_post, vec)
        if (corr is not None) and (corr > 0.0 + eps) and (corr > max_corr + eps):
            offenders.append((other_side, corr))

    if offenders:
        offenders.sort(key=lambda t: t[1], reverse=True)
        return True, {
            "reason": "high_correlation",
            "group": group,
            "threshold": max_corr,
            "offenders": offenders[:5],
            "new_bet": asdict(new_bet),
        }

    return False, {"reason": "ok", "group": group, "threshold": max_corr}
