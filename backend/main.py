import json
import os
import shutil
import subprocess
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11435")

app = FastAPI(title="Octopus")
client = httpx.AsyncClient(base_url=OLLAMA_URL, timeout=httpx.Timeout(600.0, connect=5.0))


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]


class PullRequest(BaseModel):
    model: str


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
                    eval_dur_ns = chunk.get("eval_duration", 1)
                    prompt_count = chunk.get("prompt_eval_count", 0)
                    tokens_per_sec = eval_count / (eval_dur_ns / 1e9) if eval_dur_ns else 0
                    yield _sse(
                        {
                            "type": "done",
                            "tokens_per_sec": round(tokens_per_sec, 1),
                            "eval_count": eval_count,
                            "prompt_count": prompt_count,
                            "total_ms": int((time.perf_counter() - start) * 1000),
                        }
                    )

    return StreamingResponse(stream(), media_type="text/event-stream")


def _sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()


@app.delete("/api/models/{name:path}")
async def delete_model(name: str) -> dict[str, Any]:
    """Delete a model from Ollama. `name` may include the tag (qwen3:14b)."""
    r = await client.request("DELETE", "/api/delete", json={"model": name})
    if r.status_code != 200:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=r.status_code,
            detail=f"Ollama returned {r.status_code}: {r.text}",
        )
    return {"deleted": True, "model": name}


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
