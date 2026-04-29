import json
import os
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


@app.get("/api/models")
async def list_models() -> dict[str, Any]:
    r = await client.get("/api/tags")
    return r.json()  # type: ignore[no-any-return]


@app.get("/api/loaded")
async def loaded_models() -> dict[str, Any]:
    r = await client.get("/api/ps")
    return r.json()  # type: ignore[no-any-return]


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
                if first_token_time is None and chunk.get("message", {}).get("content"):
                    first_token_time = time.perf_counter()
                    ttft_ms = int((first_token_time - start) * 1000)
                    yield _sse({"type": "ttft", "ms": ttft_ms})
                if "message" in chunk and chunk["message"].get("content"):
                    yield _sse({"type": "token", "content": chunk["message"]["content"]})
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
