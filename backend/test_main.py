import json
import subprocess
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import main
from main import _sse, app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_unknown_route_returns_404(client: TestClient) -> None:
    """App is wired up: unknown route gives 404, not 500."""
    r = client.get("/api/nonexistent")
    assert r.status_code == 404


def test_sse_helper_formats_payload() -> None:
    out = _sse({"type": "token", "content": "hi"})
    assert out == b'data: {"type": "token", "content": "hi"}\n\n'


def test_sse_helper_handles_unicode() -> None:
    out = _sse({"type": "token", "content": "🐙"})
    decoded = out.decode("utf-8")
    assert decoded.startswith("data: ")
    assert decoded.endswith("\n\n")


def test_list_models_proxies_ollama(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    fake = {"models": [{"name": "fake:1b"}]}
    mock_resp = MagicMock()
    mock_resp.json.return_value = fake
    monkeypatch.setattr(main, "client", MagicMock(get=AsyncMock(return_value=mock_resp)))
    r = client.get("/api/models")
    assert r.status_code == 200
    assert r.json() == fake


def test_loaded_models_proxies_ollama(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    fake: dict[str, list[Any]] = {"models": []}
    mock_resp = MagicMock()
    mock_resp.json.return_value = fake
    monkeypatch.setattr(main, "client", MagicMock(get=AsyncMock(return_value=mock_resp)))
    r = client.get("/api/loaded")
    assert r.status_code == 200
    assert r.json() == fake


def test_ollama_info_when_reachable(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"version": "0.17.4"}
    monkeypatch.setattr(main, "client", MagicMock(get=AsyncMock(return_value=mock_resp)))
    r = client.get("/api/ollama")
    assert r.status_code == 200
    body = r.json()
    assert body["reachable"] is True
    assert body["version"] == "0.17.4"
    assert "url" in body


def test_ollama_info_when_unreachable(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    import httpx

    def raise_connect_error(*_: Any, **__: Any) -> None:
        raise httpx.ConnectError("nope")

    monkeypatch.setattr(main, "client", MagicMock(get=AsyncMock(side_effect=raise_connect_error)))
    r = client.get("/api/ollama")
    assert r.status_code == 200
    body = r.json()
    assert body["reachable"] is False
    assert body["version"] is None


def test_delete_model_success(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    monkeypatch.setattr(main, "client", MagicMock(request=AsyncMock(return_value=mock_resp)))
    r = client.delete("/api/models/qwen3:14b")
    assert r.status_code == 200
    body = r.json()
    assert body["deleted"] is True
    assert body["model"] == "qwen3:14b"


def test_delete_model_failure_propagates_status(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "model not found"
    monkeypatch.setattr(main, "client", MagicMock(request=AsyncMock(return_value=mock_resp)))
    r = client.delete("/api/models/nonexistent:latest")
    assert r.status_code == 404


def test_pull_streams_progress_events(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    chunks = [
        json.dumps({"status": "pulling manifest"}),
        json.dumps({"status": "downloading", "total": 1000, "completed": 500}),
        json.dumps({"status": "success"}),
    ]

    class FakeStream:
        async def __aenter__(self) -> "FakeStream":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def aiter_lines(self) -> Any:
            for line in chunks:
                yield line

    fake_client = MagicMock()
    fake_client.stream = MagicMock(return_value=FakeStream())
    monkeypatch.setattr(main, "client", fake_client)

    r = client.post("/api/pull", json={"model": "fake:1b"})
    assert r.status_code == 200
    body = r.text
    assert "pulling manifest" in body
    assert '"completed": 500' in body
    assert '"status": "success"' in body


def test_host_info_returns_expected_keys(client: TestClient) -> None:
    r = client.get("/api/host")
    assert r.status_code == 200
    body = r.json()
    assert "cpu" in body
    assert "memory" in body
    assert "disk" in body
    assert "uptime_seconds" in body
    assert body["cpu"]["cores"] >= 1


def test_gpu_endpoint_when_nvidia_smi_missing(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    def raise_fnf(*_: Any, **__: Any) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "check_output", raise_fnf)
    r = client.get("/api/gpu")
    assert r.status_code == 200
    assert r.json() == {"available": False}


def test_gpu_endpoint_parses_nvidia_smi_output(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    csv = "NVIDIA RTX 5070, 8000, 12000, 42, 58\n"
    monkeypatch.setattr(subprocess, "check_output", lambda *_, **__: csv)
    r = client.get("/api/gpu")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert len(body["gpus"]) == 1
    g = body["gpus"][0]
    assert g["name"] == "NVIDIA RTX 5070"
    assert g["memory_used_mb"] == 8000
    assert g["memory_total_mb"] == 12000
    assert g["utilization_pct"] == 42
    assert g["temp_c"] == 58


def test_chat_streams_ollama_chunks(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    """End-to-end: feed fake Ollama NDJSON, verify SSE events and final stats."""

    chunks = [
        json.dumps({"message": {"content": "hi"}, "done": False}),
        json.dumps({"message": {"content": " there"}, "done": False}),
        json.dumps(
            {
                "message": {"content": ""},
                "done": True,
                "eval_count": 2,
                "eval_duration": 1_000_000_000,  # 1 second in ns -> 2 tok/s
                "prompt_eval_count": 5,
            }
        ),
    ]

    class FakeStream:
        async def __aenter__(self) -> "FakeStream":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def aiter_lines(self) -> Any:
            for line in chunks:
                yield line

    fake_client = MagicMock()
    fake_client.stream = MagicMock(return_value=FakeStream())
    monkeypatch.setattr(main, "client", fake_client)

    r = client.post(
        "/api/chat",
        json={"model": "fake", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert r.status_code == 200
    body = r.text
    assert "ttft" in body
    assert '"content": "hi"' in body
    assert '"content": " there"' in body
    assert '"tokens_per_sec": 2.0' in body
    assert '"eval_count": 2' in body


def test_chat_forwards_thinking_field_for_reasoning_models(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """qwen3 / deepseek-r1 etc. stream into `thinking` before `content`.
    The backend must forward both so the UI doesn't appear frozen."""
    chunks = [
        json.dumps({"message": {"content": "", "thinking": "Let me think"}, "done": False}),
        json.dumps({"message": {"content": "", "thinking": " about it"}, "done": False}),
        json.dumps({"message": {"content": "Hi"}, "done": False}),
        json.dumps(
            {
                "message": {"content": ""},
                "done": True,
                "eval_count": 1,
                "eval_duration": 1_000_000_000,
                "prompt_eval_count": 5,
            }
        ),
    ]

    class FakeStream:
        async def __aenter__(self) -> "FakeStream":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def aiter_lines(self) -> Any:
            for line in chunks:
                yield line

    fake_client = MagicMock()
    fake_client.stream = MagicMock(return_value=FakeStream())
    monkeypatch.setattr(main, "client", fake_client)

    r = client.post(
        "/api/chat",
        json={"model": "qwen3:14b", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    body = r.text
    assert '"type": "thinking"' in body
    assert '"content": "Let me think"' in body
    assert '"content": " about it"' in body
    assert '"type": "token"' in body
    assert '"content": "Hi"' in body
