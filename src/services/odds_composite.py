"""
AsianConnect Prematch Odds Composite
------------------------------------
Combines Pinnacle, SBO, and ISN odds into a weighted sharp composite.
Uses dummy data in demo mode (no live broker creds required).
"""

from __future__ import annotations
import random, time
import pandas as pd

# Default weights (can override via config)
WEIGHTS = {"pinnacle": 0.50, "sbo": 0.30, "isn": 0.20}

def _simulate_odds_row(book: str) -> dict:
    """Simulate one prematch odds row for a given book."""
    base = random.uniform(1.80, 2.20)
    return {
        "book": book,
        "home_odds": round(base, 3),
        "away_odds": round(1 / (1 - (1 / base)), 3),
        "timestamp": time.time(),
    }

def fetch_from_broker(book: str, match_id: str) -> dict:
    """Stub for AsianConnect API call."""
    # In production, this will call the AC API endpoint with creds.
    # Here we simulate with pseudo-random odds.
    return _simulate_odds_row(book)

def compute_composite_odds(match_id: str, weights: dict = None) -> dict:
    """Fetch odds from Pinnacle/SBO/ISN and compute weighted sharp composite."""
    w = weights or WEIGHTS
    books = ["pinnacle", "sbo", "isn"]
    rows = [fetch_from_broker(b, match_id) for b in books]
    df = pd.DataFrame(rows)

    # Convert odds → implied probability
    df["home_prob"] = 1 / df["home_odds"]
    df["away_prob"] = 1 / df["away_odds"]

    # Weighted composite
    home_comp = sum(df.loc[df["book"] == b, "home_prob"].iloc[0] * w[b] for b in books)
    away_comp = sum(df.loc[df["book"] == b, "away_prob"].iloc[0] * w[b] for b in books)

    # Normalize
    s = home_comp + away_comp
    home_final, away_final = home_comp / s, away_comp / s

    return {
        "match_id": match_id,
        "home_prob": round(home_final, 4),
        "away_prob": round(away_final, 4),
        "sharp_books_used": len(books),
        "timestamp": time.time(),
    }

if __name__ == "__main__":
    print(compute_composite_odds("EPL_2025_ARS_TOT"))
