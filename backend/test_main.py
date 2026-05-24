import asyncio
import json
import subprocess
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
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


def test_unload_model_success(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    post_mock = AsyncMock(return_value=mock_resp)
    monkeypatch.setattr(main, "client", MagicMock(post=post_mock))
    r = client.post("/api/models/qwen3:14b/unload")
    assert r.status_code == 200
    body = r.json()
    assert body["unloaded"] is True
    assert body["model"] == "qwen3:14b"
    # Confirm we used the documented keep_alive=0 unload idiom on /api/generate
    post_mock.assert_awaited_once()
    args, kwargs = post_mock.call_args
    assert args[0] == "/api/generate"
    assert kwargs["json"] == {"model": "qwen3:14b", "keep_alive": 0}


def test_unload_model_failure_propagates_status(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "model not found"
    monkeypatch.setattr(main, "client", MagicMock(post=AsyncMock(return_value=mock_resp)))
    r = client.post("/api/models/nonexistent:latest/unload")
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


def test_chat_skips_blank_and_unparseable_lines(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """Empty lines and JSON decode errors must not crash the stream."""
    chunks = [
        "",  # blank — `if not raw: continue`
        "not json at all",  # bad JSON — `except JSONDecodeError: continue`
        json.dumps({"message": {"content": "ok"}, "done": False}),
        json.dumps(
            {"message": {"content": ""}, "done": True, "eval_count": 1, "eval_duration": 0}
        ),  # eval_duration=0 -> tokens_per_sec=0 branch
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
        json={"model": "fake", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    assert '"content": "ok"' in r.text
    assert '"tokens_per_sec": 0' in r.text


def test_pull_skips_blank_and_unparseable_lines(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    chunks = [
        "",  # blank
        "junk",  # bad JSON
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
    assert '"status": "success"' in r.text


def test_pull_emits_error_on_request_failure(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """If the upstream fetch dies, the SSE stream must emit a `status: error`
    event rather than tearing down the connection."""
    import httpx

    class BoomStream:
        async def __aenter__(self) -> "BoomStream":
            raise httpx.ConnectError("ollama gone")

        async def __aexit__(self, *_: Any) -> None:
            return None

    fake_client = MagicMock()
    fake_client.stream = MagicMock(return_value=BoomStream())
    monkeypatch.setattr(main, "client", fake_client)
    r = client.post("/api/pull", json={"model": "fake:1b"})
    assert r.status_code == 200
    assert '"status": "error"' in r.text
    assert "ollama gone" in r.text


def test_check_disk_thresholds(monkeypatch: pytest.MonkeyPatch) -> None:
    """_check_disk maps free GB into pass/warn/fail tiers."""
    import shutil as _shutil
    from collections import namedtuple

    Usage = namedtuple("Usage", ["total", "used", "free"])

    async def call() -> dict[str, Any]:
        return await main._check_disk()

    # pass: >10 GB
    monkeypatch.setattr(_shutil, "disk_usage", lambda _: Usage(0, 0, 50 * 10**9))
    res = pytest.run(call) if False else __import__("asyncio").run(call())
    assert res["status"] == "pass"

    # warn: between 2 and 10 GB
    monkeypatch.setattr(_shutil, "disk_usage", lambda _: Usage(0, 0, 5 * 10**9))
    res = __import__("asyncio").run(call())
    assert res["status"] == "warn"

    # fail: under 2 GB
    monkeypatch.setattr(_shutil, "disk_usage", lambda _: Usage(0, 0, 1 * 10**9))
    res = __import__("asyncio").run(call())
    assert res["status"] == "fail"

    # OSError path
    def boom(_: Any) -> None:
        raise OSError("nope")

    monkeypatch.setattr(_shutil, "disk_usage", boom)
    res = __import__("asyncio").run(call())
    assert res["status"] == "fail"


def test_check_ollama_pass_and_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """_check_ollama handles 200, non-200, and connection error."""

    import httpx as _httpx

    # pass
    ok = MagicMock()
    ok.status_code = 200
    ok.json.return_value = {"version": "1.2.3"}
    monkeypatch.setattr(main, "client", MagicMock(get=AsyncMock(return_value=ok)))
    res = asyncio.run(main._check_ollama())
    assert res["status"] == "pass"
    assert "1.2.3" in res["detail"]

    # non-200
    bad = MagicMock()
    bad.status_code = 503
    monkeypatch.setattr(main, "client", MagicMock(get=AsyncMock(return_value=bad)))
    res = asyncio.run(main._check_ollama())
    assert res["status"] == "fail"
    assert "503" in res["detail"]

    # connect error
    def raise_connect(*_: Any, **__: Any) -> None:
        raise _httpx.ConnectError("down")

    monkeypatch.setattr(main, "client", MagicMock(get=AsyncMock(side_effect=raise_connect)))
    res = asyncio.run(main._check_ollama())
    assert res["status"] == "fail"
    assert "unreachable" in res["detail"]


def test_check_audit_scans_frontend(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """_check_audit walks frontend/src and reports forbidden patterns."""

    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.svelte").write_text("export const x = 1;\n", encoding="utf-8")
    (src / "leaky.js").write_text(
        "const apiKey = 'abc';\nconsole.log('debug');\n", encoding="utf-8"
    )

    monkeypatch.setattr(main, "FRONTEND_DIR", tmp_path)
    monkeypatch.setattr(main, "REPO_ROOT", tmp_path)
    res = asyncio.run(main._check_audit())
    # Two patterns trip in leaky.js — both reported, no exception, status warn.
    assert res["status"] == "warn"
    assert "console.log" in res["detail"]


def test_check_audit_clean_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:

    src = tmp_path / "src"
    src.mkdir()
    (src / "clean.svelte").write_text("export const x = 1;\n", encoding="utf-8")
    monkeypatch.setattr(main, "FRONTEND_DIR", tmp_path)
    monkeypatch.setattr(main, "REPO_ROOT", tmp_path)
    res = asyncio.run(main._check_audit())
    assert res["status"] == "pass"
    assert "scanned" in res["detail"]


def test_parse_version_extracts_triple() -> None:
    assert main._parse_version("0.17.4") == (0, 17, 4)
    assert main._parse_version("v1.2.3") == (1, 2, 3)
    assert main._parse_version("garbage") is None
    assert main._parse_version("") is None


def test_check_ollama_version_update_pass_warn_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pass when local >= latest, warn when local < latest, warn on network error."""

    local_resp = MagicMock()
    local_resp.status_code = 200
    local_resp.json.return_value = {"version": "0.17.4"}
    monkeypatch.setattr(main, "client", MagicMock(get=AsyncMock(return_value=local_resp)))

    def make_gh_client(tag: str) -> Any:
        gh_resp = MagicMock()
        gh_resp.status_code = 200
        gh_resp.json.return_value = {"tag_name": tag}
        instance = MagicMock()
        instance.get = AsyncMock(return_value=gh_resp)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=None)
        return MagicMock(return_value=instance)

    # pass — local == latest
    monkeypatch.setattr(httpx, "AsyncClient", make_gh_client("v0.17.4"))
    res = asyncio.run(main._check_ollama_version_update())
    assert res["status"] == "pass"
    assert "0.17.4" in res["detail"]

    # warn — local < latest
    monkeypatch.setattr(httpx, "AsyncClient", make_gh_client("v0.18.0"))
    res = asyncio.run(main._check_ollama_version_update())
    assert res["status"] == "warn"
    assert "0.18.0" in res["detail"]

    # warn — github unreachable
    def boom_client(*_a: Any, **_kw: Any) -> Any:
        instance = MagicMock()
        instance.get = AsyncMock(side_effect=httpx.ConnectError("down"))
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=None)
        return instance

    monkeypatch.setattr(httpx, "AsyncClient", boom_client)
    res = asyncio.run(main._check_ollama_version_update())
    assert res["status"] == "warn"
    assert "unreachable" in res["detail"]


def test_check_ollama_model_updates_detects_stale_and_skips_user_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mismatched digest → stale; namespaced models (foo/bar) → skipped."""

    tags_resp = MagicMock()
    tags_resp.status_code = 200
    tags_resp.json.return_value = {
        "models": [
            {"name": "gemma3:12b", "digest": "aaa"},  # stale (registry returns bbb)
            {"name": "nomic-embed-text:latest", "digest": "ccc"},  # fresh
            {"name": "user/custom:1", "digest": "ddd"},  # skipped
        ]
    }
    monkeypatch.setattr(main, "client", MagicMock(get=AsyncMock(return_value=tags_resp)))

    def reg_head(url: str, headers: Any = None) -> Any:
        resp = MagicMock()
        resp.status_code = 200
        if "gemma3" in url:
            resp.headers = {"docker-content-digest": "sha256:bbb"}
        else:
            resp.headers = {"docker-content-digest": "sha256:ccc"}
        return resp

    instance = MagicMock()
    instance.head = AsyncMock(side_effect=reg_head)
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(httpx, "AsyncClient", MagicMock(return_value=instance))

    res = asyncio.run(main._check_ollama_model_updates())
    assert res["status"] == "warn"
    assert "gemma3:12b" in res["detail"]
    assert "nomic-embed-text" not in res["detail"]


def _fake_proc(stdout_bytes: bytes) -> Any:
    """Build a fake asyncio subprocess that returns the given stdout."""
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout_bytes, b""))
    proc.kill = MagicMock()
    proc.wait = AsyncMock(return_value=None)
    return proc


def test_check_npm_outdated_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty {} → pass, populated → warn with package names."""

    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", AsyncMock(return_value=_fake_proc(b"{}"))
    )
    assert asyncio.run(main._check_npm_outdated())["status"] == "pass"

    payload = json.dumps({"vite": {}, "eslint": {}}).encode()
    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", AsyncMock(return_value=_fake_proc(payload))
    )
    res = asyncio.run(main._check_npm_outdated())
    assert res["status"] == "warn"
    assert "vite" in res["detail"]
    assert "eslint" in res["detail"]


def test_check_pip_outdated_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty [] → pass, populated → warn with package names."""

    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", AsyncMock(return_value=_fake_proc(b"[]"))
    )
    assert asyncio.run(main._check_pip_outdated())["status"] == "pass"

    payload = json.dumps([{"name": "ruff"}, {"name": "mypy"}]).encode()
    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", AsyncMock(return_value=_fake_proc(payload))
    )
    res = asyncio.run(main._check_pip_outdated())
    assert res["status"] == "warn"
    assert "ruff" in res["detail"]
    assert "mypy" in res["detail"]


def test_run_shell_pass_and_fail(tmp_path: Any) -> None:
    """_run_shell wraps subprocess; verify pass, fail, and missing-binary paths."""

    # pass — `true` exits 0
    res = asyncio.run(main._run_shell(["true"], tmp_path))
    assert res["status"] == "pass"

    # fail — `false` exits 1
    res = asyncio.run(main._run_shell(["false"], tmp_path))
    assert res["status"] == "fail"

    # missing binary
    res = asyncio.run(main._run_shell(["definitely-not-a-real-binary-xyz"], tmp_path))
    assert res["status"] == "fail"
    assert "missing binary" in res["detail"]


def test_diagnostic_checks_endpoint_lists_all_checks(client: TestClient) -> None:
    r = client.get("/api/diagnostic/checks")
    assert r.status_code == 200
    body = r.json()
    ids = {c["id"] for c in body["checks"]}
    # Sanity: a representative subset must be present.
    assert {"ollama", "disk", "audit"}.issubset(ids)
    for c in body["checks"]:
        assert {"id", "name", "category"} <= c.keys()


def test_run_diagnostic_streams_summary(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """End-to-end: run_diagnostic with stubbed checks emits start, per-check,
    and a final done event with a summary."""

    async def stub_pass() -> dict[str, Any]:
        return {"status": "pass", "detail": "ok"}

    async def stub_fail() -> dict[str, Any]:
        return {"status": "fail", "detail": "bad"}

    async def stub_raises() -> dict[str, Any]:
        raise RuntimeError("kaboom")

    monkeypatch.setattr(
        main,
        "_DIAGNOSTIC_CHECKS",
        [
            ("a", "first", "runtime", stub_pass),
            ("b", "second", "code", stub_fail),
            ("c", "third", "audit", stub_raises),
        ],
    )
    r = client.post("/api/diagnostic")
    assert r.status_code == 200
    body = r.text
    assert '"type": "start"' in body
    assert '"type": "running"' in body
    assert '"type": "check"' in body
    assert '"type": "done"' in body
    # Raised exception becomes a visible fail row.
    assert "check raised" in body
    # Summary should reflect 1 pass and 2 fail.
    assert '"pass": 1' in body
    assert '"fail": 2' in body


# --- Validation -------------------------------------------------------------


def test_chat_rejects_path_traversal_in_model_name(client: TestClient) -> None:
    """Model name containing `..` is rejected before reaching Ollama."""
    r = client.post(
        "/api/chat",
        json={"model": "../etc/passwd", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 422


def test_chat_rejects_invalid_model_name_chars(client: TestClient) -> None:
    """Model name with spaces or control characters is rejected."""
    r = client.post(
        "/api/chat",
        json={"model": "bad name", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 422


def test_chat_rejects_invalid_role(client: TestClient) -> None:
    """ChatMessage rejects roles outside the allowed set."""
    r = client.post(
        "/api/chat",
        json={"model": "qwen3:14b", "messages": [{"role": "system_hack", "content": "x"}]},
    )
    assert r.status_code == 422


def test_pull_rejects_invalid_model_name(client: TestClient) -> None:
    r = client.post("/api/pull", json={"model": "../foo"})
    assert r.status_code == 422


def test_delete_model_rejects_path_traversal(client: TestClient) -> None:
    """A `..` segment in the URL path must be rejected by the validator."""
    # FastAPI's path converter normalises some traversal at the URL layer; the
    # validator catches the rest.
    r = client.delete("/api/models/foo/..%2Fbar")
    # Either FastAPI 404s the URL or our validator rejects it — both safe.
    assert r.status_code in (400, 404)


def test_chat_emits_error_on_request_failure(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """If Ollama is unreachable, the stream surfaces a structured error event."""

    class FailingStream:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        async def __aenter__(self) -> "FailingStream":
            raise httpx.ConnectError("ollama down")

        async def __aexit__(self, *_: Any) -> None:
            return None

    fake_client = MagicMock()
    fake_client.stream = MagicMock(side_effect=lambda *a, **k: FailingStream())
    monkeypatch.setattr(main, "client", fake_client)
    r = client.post(
        "/api/chat",
        json={"model": "qwen3:14b", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    assert '"type": "error"' in r.text
    assert "ollama down" in r.text
