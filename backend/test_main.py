from fastapi.testclient import TestClient

from main import app


def test_app_starts():
    """Smoke test: app instantiates and routes are registered."""
    client = TestClient(app)
    # We don't hit Ollama here — just confirm the app object responds with 404 (not 500)
    # for an unknown route, which means it's wired up.
    r = client.get("/api/nonexistent")
    assert r.status_code == 404


def test_gpu_endpoint_shape():
    """/api/gpu should return a dict with 'available' key whether or not nvidia-smi exists."""
    client = TestClient(app)
    r = client.get("/api/gpu")
    assert r.status_code == 200
    data = r.json()
    assert "available" in data
    if data["available"]:
        assert "gpus" in data
        assert isinstance(data["gpus"], list)
