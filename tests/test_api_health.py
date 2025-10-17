# tests/test_api_health.py
from fastapi.testclient import TestClient
from src.serve.api import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("ok") is True
