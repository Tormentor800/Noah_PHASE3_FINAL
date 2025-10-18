from __future__ import annotations
from fastapi import FastAPI
from time import time

app = FastAPI(title="Noah API", version="1.0.0")
START = time()

@app.get("/")
def root():
    return {"name": "noah-api", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok", "uptime": round(time() - START, 2)}
