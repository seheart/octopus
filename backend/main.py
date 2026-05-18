import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

# Ollama model identifiers: alnum + `_ . : / -`. We additionally reject `..`
# and leading `/` so a malformed name can't trick a downstream component into
# walking the filesystem if it ever interprets it as a path.
_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9_./:-]{1,200}$")


def _validate_model_name(name: str) -> str:
    if not _MODEL_NAME_RE.match(name) or ".." in name or name.startswith("/"):
        raise HTTPException(status_code=400, detail="invalid model name")
    return name


client = httpx.AsyncClient(base_url=OLLAMA_URL, timeout=httpx.Timeout(600.0, connect=5.0))


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Own the global httpx client's lifecycle — close it on shutdown."""
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(title="Octopus", lifespan=lifespan)


class ChatMessage(BaseModel):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def _check_role(cls, v: str) -> str:
        if v not in {"user", "assistant", "system"}:
            raise ValueError(f"invalid role: {v!r}")
        return v


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]

    @field_validator("model")
    @classmethod
    def _check_model(cls, v: str) -> str:
        if not _MODEL_NAME_RE.match(v) or ".." in v or v.startswith("/"):
            raise ValueError("invalid model name")
        return v


class PullRequest(BaseModel):
    model: str

    @field_validator("model")
    @classmethod
    def _check_model(cls, v: str) -> str:
        if not _MODEL_NAME_RE.match(v) or ".." in v or v.startswith("/"):
            raise ValueError("invalid model name")
        return v


@app.get("/api/models")
async def list_models() -> dict[str, Any]:
    r = await client.get("/api/tags")
    return r.json()  # type: ignore[no-any-return]


@app.get("/api/loaded")
async def loaded_models() -> dict[str, Any]:
    r = await client.get("/api/ps")
    return r.json()  # type: ignore[no-any-return]


@app.get("/api/ollama")
async def ollama_info() -> dict[str, Any]:
    """Ollama version + connection status."""
    try:
        r = await client.get("/api/version", timeout=2.0)
        version = r.json().get("version") if r.status_code == 200 else None
        return {
            "reachable": True,
            "version": version,
            "url": OLLAMA_URL,
        }
    except (httpx.RequestError, httpx.HTTPStatusError):
        return {"reachable": False, "version": None, "url": OLLAMA_URL}


@app.get("/api/host")
def host_info() -> dict[str, Any]:
    """Host system info (CPU, RAM, disk) parsed from /proc + shutil."""
    info: dict[str, Any] = {}

    # CPU
    cpu_model = "unknown"
    cpu_count = os.cpu_count() or 0
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    cpu_model = line.split(":", 1)[1].strip()
                    break
    except OSError:
        pass
    info["cpu"] = {"model": cpu_model, "cores": cpu_count}

    # Memory
    try:
        meminfo: dict[str, int] = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, _, rest = line.partition(":")
                value_str = rest.strip().split()[0]
                meminfo[key.strip()] = int(value_str) * 1024  # kB → bytes
        total = meminfo.get("MemTotal", 0)
        available = meminfo.get("MemAvailable", 0)
        info["memory"] = {
            "total_bytes": total,
            "available_bytes": available,
            "used_bytes": total - available,
        }
    except (OSError, ValueError, IndexError):
        info["memory"] = None

    # Disk (root filesystem)
    try:
        usage = shutil.disk_usage("/")
        info["disk"] = {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
        }
    except OSError:
        info["disk"] = None

    # Uptime (best-effort)
    try:
        with open("/proc/uptime") as f:
            info["uptime_seconds"] = float(f.read().split()[0])
    except (OSError, ValueError):
        info["uptime_seconds"] = None

    return info


@app.get("/api/gpu")
def gpu_stats() -> dict[str, Any]:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=2,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return {"available": False}
    gpus = []
    for line in out.strip().splitlines():
        name, used, total, util, temp = (p.strip() for p in line.split(","))
        gpus.append(
            {
                "name": name,
                "memory_used_mb": int(used),
                "memory_total_mb": int(total),
                "utilization_pct": int(util),
                "temp_c": int(temp),
            }
        )
    return {"available": True, "gpus": gpus}


@app.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    async def stream() -> AsyncIterator[bytes]:
        start = time.perf_counter()
        first_token_time: float | None = None
        try:
            async with client.stream(
                "POST",
                "/api/chat",
                json={
                    "model": req.model,
                    "messages": [m.model_dump() for m in req.messages],
                    "stream": True,
                },
            ) as resp:
                async for raw in resp.aiter_lines():
                    if not raw:
                        continue
                    try:
                        chunk = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    msg = chunk.get("message", {})
                    # Reasoning models (qwen3, deepseek-r1, etc.) stream into
                    # `thinking` before producing `content`. Forward both so the
                    # UI can show the model is alive instead of silently waiting.
                    if msg.get("thinking"):
                        yield _sse({"type": "thinking", "content": msg["thinking"]})
                    if first_token_time is None and msg.get("content"):
                        first_token_time = time.perf_counter()
                        ttft_ms = int((first_token_time - start) * 1000)
                        yield _sse({"type": "ttft", "ms": ttft_ms})
                    if msg.get("content"):
                        yield _sse({"type": "token", "content": msg["content"]})
                    if chunk.get("done"):
                        eval_count = chunk.get("eval_count", 0)
                        # eval_duration may be 0 or missing on early stops or
                        # malformed payloads — treat both as "no measurement".
                        eval_dur_ns = chunk.get("eval_duration") or 0
                        prompt_count = chunk.get("prompt_eval_count", 0)
                        tokens_per_sec = eval_count / (eval_dur_ns / 1e9) if eval_dur_ns > 0 else 0
                        yield _sse(
                            {
                                "type": "done",
                                "tokens_per_sec": round(tokens_per_sec, 1),
                                "eval_count": eval_count,
                                "prompt_count": prompt_count,
                                "total_ms": int((time.perf_counter() - start) * 1000),
                            }
                        )
        except httpx.RequestError as e:
            # Ollama unreachable or connection dropped mid-stream — surface
            # a structured error event instead of a truncated SSE response.
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(stream(), media_type="text/event-stream")


def _sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()


@app.delete("/api/models/{name:path}")
async def delete_model(name: str) -> dict[str, Any]:
    """Delete a model from Ollama. `name` may include the tag (qwen3:14b)."""
    name = _validate_model_name(name)
    r = await client.request("DELETE", "/api/delete", json={"model": name})
    if r.status_code != 200:
        raise HTTPException(
            status_code=r.status_code,
            detail=f"Ollama returned {r.status_code}",
        )
    return {"deleted": True, "model": name}


@app.post("/api/models/{name:path}/unload")
async def unload_model(name: str) -> dict[str, Any]:
    """Evict a model from memory without deleting it.

    Uses Ollama's documented `keep_alive: 0` idiom — a no-op generate request
    that tells the runtime to release the model immediately.
    """
    name = _validate_model_name(name)
    r = await client.post("/api/generate", json={"model": name, "keep_alive": 0})
    if r.status_code != 200:
        raise HTTPException(
            status_code=r.status_code,
            detail=f"Ollama returned {r.status_code}",
        )
    return {"unloaded": True, "model": name}


@app.post("/api/pull")
async def pull_model(req: PullRequest) -> StreamingResponse:
    """Stream Ollama's pull progress as SSE.

    Events: {"status": "..."} for steps, with optional total/completed/digest
    during the downloading phase. Final event is {"status": "success"}.
    """

    async def stream() -> AsyncIterator[bytes]:
        try:
            async with client.stream(
                "POST",
                "/api/pull",
                json={"model": req.model, "stream": True},
                timeout=httpx.Timeout(3600.0, connect=5.0),
            ) as resp:
                async for raw in resp.aiter_lines():
                    if not raw:
                        continue
                    try:
                        chunk = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    yield _sse(chunk)
        except httpx.RequestError as e:
            yield _sse({"status": "error", "error": str(e)})

    return StreamingResponse(stream(), media_type="text/event-stream")


# --- Diagnostic ---------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"


async def _run_shell(cmd: list[str], cwd: Path, timeout: float = 120.0) -> dict[str, Any]:
    """Run a shell command, return {status, detail} where status is pass/fail."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            return {"status": "fail", "detail": f"timed out after {timeout:.0f}s"}
        text = stdout.decode("utf-8", errors="replace").strip()
        # Trim noise — keep last ~40 lines so the UI excerpt stays useful.
        lines = text.splitlines()
        excerpt = "\n".join(lines[-40:]) if len(lines) > 40 else text
        if proc.returncode == 0:
            return {"status": "pass", "detail": excerpt or "ok"}
        return {"status": "fail", "detail": excerpt or f"exit {proc.returncode}"}
    except FileNotFoundError as e:
        return {"status": "fail", "detail": f"missing binary: {e.filename}"}


async def _check_ollama() -> dict[str, Any]:
    try:
        r = await client.get("/api/version", timeout=2.0)
        if r.status_code == 200:
            v = r.json().get("version", "?")
            return {"status": "pass", "detail": f"version {v} on {OLLAMA_URL}"}
        return {"status": "fail", "detail": f"HTTP {r.status_code} from {OLLAMA_URL}"}
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        return {"status": "fail", "detail": f"unreachable: {e}"}


async def _check_disk() -> dict[str, Any]:
    try:
        usage = shutil.disk_usage("/")
        gb_free = usage.free / 1e9
        if gb_free < 2:
            return {"status": "fail", "detail": f"only {gb_free:.1f} GB free on root"}
        if gb_free < 10:
            return {"status": "warn", "detail": f"{gb_free:.1f} GB free on root"}
        return {"status": "pass", "detail": f"{gb_free:.1f} GB free on root"}
    except OSError as e:
        return {"status": "fail", "detail": str(e)}


# Patterns we never want to ship — secrets, debug leftovers.
_AUDIT_PATTERNS = [
    (
        re.compile(r"(?i)\b(api[_-]?key|secret|password|bearer\s+[A-Za-z0-9_\-]{16,})\s*[:=]"),
        "possible credential literal",
    ),
    (re.compile(r"console\.log\("), "console.log left in source"),
    (re.compile(r"\bdebugger\b"), "debugger statement"),
]


async def _check_audit() -> dict[str, Any]:
    findings: list[str] = []
    targets = list((FRONTEND_DIR / "src").rglob("*.svelte")) + list(
        (FRONTEND_DIR / "src").rglob("*.js")
    )
    for path in targets:
        if "node_modules" in path.parts or ".test." in path.name or ".spec." in path.name:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern, label in _AUDIT_PATTERNS:
            for m in pattern.finditer(text):
                line_no = text.count("\n", 0, m.start()) + 1
                rel = path.relative_to(REPO_ROOT)
                findings.append(f"{rel}:{line_no}  {label}")
                if len(findings) >= 20:
                    break
            if len(findings) >= 20:
                break
        if len(findings) >= 20:
            break
    if not findings:
        return {"status": "pass", "detail": f"scanned {len(targets)} files, no findings"}
    detail = "\n".join(findings)
    return {"status": "warn", "detail": detail}


CheckFn = Callable[[], Awaitable[dict[str, Any]]]
# (id, label, category, fn). Category groups the UI; order is run order.
_DIAGNOSTIC_CHECKS: list[tuple[str, str, str, CheckFn]] = [
    ("ollama", "Ollama reachable", "runtime", _check_ollama),
    ("disk", "Disk free on root", "runtime", _check_disk),
    (
        "backend_lint",
        "backend · ruff lint",
        "code",
        lambda: _run_shell([".venv/bin/ruff", "check", "."], BACKEND_DIR),
    ),
    (
        "backend_format",
        "backend · ruff format",
        "code",
        lambda: _run_shell([".venv/bin/ruff", "format", "--check", "."], BACKEND_DIR),
    ),
    (
        "backend_types",
        "backend · mypy",
        "code",
        lambda: _run_shell([".venv/bin/mypy", "."], BACKEND_DIR),
    ),
    (
        "backend_tests",
        "backend · pytest",
        "code",
        lambda: _run_shell([".venv/bin/pytest", "-q"], BACKEND_DIR),
    ),
    (
        "frontend_types",
        "frontend · svelte-check",
        "code",
        lambda: _run_shell(["npm", "run", "check"], FRONTEND_DIR),
    ),
    (
        "frontend_lint",
        "frontend · eslint",
        "code",
        lambda: _run_shell(["npm", "run", "lint"], FRONTEND_DIR),
    ),
    (
        "frontend_tests",
        "frontend · vitest",
        "code",
        lambda: _run_shell(["npm", "run", "test"], FRONTEND_DIR),
    ),
    ("audit", "audit · secrets / debug leftovers", "audit", _check_audit),
]


@app.get("/api/diagnostic/checks")
def diagnostic_checks() -> dict[str, Any]:
    """List the checks the diagnostic will run, so the UI can render them up front."""
    return {
        "checks": [
            {"id": cid, "name": name, "category": cat} for cid, name, cat, _ in _DIAGNOSTIC_CHECKS
        ]
    }


@app.post("/api/diagnostic")
async def run_diagnostic() -> StreamingResponse:
    """Run every diagnostic check, streaming results as each finishes (SSE)."""

    async def stream() -> AsyncIterator[bytes]:
        run_start = time.perf_counter()
        summary = {"pass": 0, "warn": 0, "fail": 0}
        yield _sse({"type": "start", "total": len(_DIAGNOSTIC_CHECKS)})
        for cid, name, category, fn in _DIAGNOSTIC_CHECKS:
            yield _sse({"type": "running", "id": cid})
            t0 = time.perf_counter()
            try:
                result = await fn()
            except Exception as e:
                # Any uncaught error becomes a visible "fail" row instead of killing the stream.
                result = {"status": "fail", "detail": f"check raised: {e}"}
            ms = int((time.perf_counter() - t0) * 1000)
            status = result.get("status", "fail")
            summary[status] = summary.get(status, 0) + 1
            yield _sse(
                {
                    "type": "check",
                    "id": cid,
                    "name": name,
                    "category": category,
                    "status": status,
                    "duration_ms": ms,
                    "detail": result.get("detail", ""),
                }
            )
        yield _sse(
            {
                "type": "done",
                "summary": summary,
                "duration_ms": int((time.perf_counter() - run_start) * 1000),
            }
        )

    return StreamingResponse(stream(), media_type="text/event-stream")
