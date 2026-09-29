from fastapi.testclient import TestClient

from app.main import app


def test_before_memory_has_no_evidence():
    with TestClient(app) as client:
        response = client.post("/api/demo/before-memory", json={"question": "Prepare me for my next call."})
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "Without Hindsight memory"
    assert body["supporting_memories"] == []

