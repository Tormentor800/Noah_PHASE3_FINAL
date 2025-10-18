from __future__ import annotations
from fastapi import FastAPI, Query
from time import time
from src.services.odds_composite import OddsComposite

app = FastAPI(title="Noah API", version="1.0.0")
START = time()
oc = OddsComposite()

@app.get("/")
def root():
    return {"name": "noah-api", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok", "uptime": round(time() - START, 2)}

@app.get("/composite")
def composite(league: str = Query(...), market: str = Query(...), base_odds: float = 1.95):
    return oc.compose({"league": league, "market": market, "base_odds": base_odds, "ts": None})
