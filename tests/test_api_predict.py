# tests/test_api_predict.py
from fastapi.testclient import TestClient
from src.serve.api import app

client = TestClient(app)

def test_predict_minimal():
    payload = {"features": {"feat_a": 0.7, "feat_b": 1.1}}
    r = client.post("/predict", json=payload)
    # If auto-disable is ON due to KPI guards, we allow 503; otherwise expect 200
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        body = r.json()
        assert "version" in body
        assert "prob" in body
        assert "edge_bp" in body
