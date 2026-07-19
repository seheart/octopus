import asyncio
import ipaddress
import json
import logging
import os
import re
import shutil
import subprocess
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("octopus")


def _resolve_ollama_url() -> str:
    raw = os.environ.get("OLLAMA_URL")
    if not raw:
        if host := os.environ.get("OLLAMA_HOST"):
            raw = host if host.startswith(("http://", "https://")) else f"http://{host}"
        else:
            raw = "http://127.0.0.1:11434"
    # `0.0.0.0` / `::` are *listen* addresses, not connectable ones — typical
    # when inheriting a systemd unit's OLLAMA_HOST=0.0.0.0:PORT. Rewrite to
    # loopback so pointing Octopus at the daemon's own env just works.
    # (start.sh applies the same rewrite for its preflight probe.)
    _LISTEN_TO_LOOPBACK = {"0.0.0.0": "127.0.0.1", "::": "[::1]"}
    parsed = urlparse(raw)
    if (loopback := _LISTEN_TO_LOOPBACK.get(parsed.hostname or "")) is not None:
        netloc = f"{loopback}:{parsed.port}" if parsed.port else loopback
        raw = parsed._replace(netloc=netloc).geturl()
    # Refuse non-loopback hosts unless explicitly allowed — otherwise a stray
    # OLLAMA_URL in shell init silently exfiltrates every chat to a remote.
    if os.environ.get("OCTOPUS_ALLOW_REMOTE_OLLAMA") != "1":
        host = (urlparse(raw).hostname or "").lower()
        if host not in ("localhost", ""):
            try:
                if not ipaddress.ip_address(host).is_loopback:
                    raise RuntimeError(
                        f"OLLAMA_URL host {host!r} is not loopback. "
                        "Set OCTOPUS_ALLOW_REMOTE_OLLAMA=1 to override."
                    )
            except ValueError as e:
                raise RuntimeError(
                    f"OLLAMA_URL host {host!r} is not loopback. "
                    "Set OCTOPUS_ALLOW_REMOTE_OLLAMA=1 to override."
                ) from e
    return raw


OLLAMA_URL = _resolve_ollama_url()

# Ollama model identifiers: alnum + `_ . : / -`. We additionally reject `..`
# and leading `/` so a malformed name can't trick a downstream component into
# walking the filesystem if it ever interprets it as a path.
_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9_./:-]{1,200}$")


def _is_valid_model_name(name: str) -> bool:
    return bool(_MODEL_NAME_RE.match(name)) and ".." not in name and not name.startswith("/")


def _validate_model_name(name: str) -> str:
    if not _is_valid_model_name(name):
        raise HTTPException(status_code=400, detail="invalid model name")
    return name


# Cap the Ollama connection pool so a runaway client (or a malicious local
# script firing N concurrent chat streams) can't exhaust httpx's default
# pool and starve legitimate UI calls.
client = httpx.AsyncClient(
    base_url=OLLAMA_URL,
    timeout=httpx.Timeout(600.0, connect=5.0),
    follow_redirects=False,
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Own the global httpx client's lifecycle — close it on shutdown."""
    try:
        yield
    finally:
        await client.aclose()


# Only the Vite dev server and the bundled-prod entrypoint should drive the
# API. We accept missing Origin (curl/local scripts/SSR), 127.0.0.1, and
# localhost. Everything else is a malicious-tab attempt and gets rejected
# before the handler runs. Reads (GET/HEAD/OPTIONS) are still open — they
# carry no side effects and the response body is opaque to other origins
# anyway thanks to default CORS.
_ALLOWED_ORIGINS = frozenset(
    {
        "http://127.0.0.1:8801",
        "http://localhost:8801",
        # The bundled prod page is served by uvicorn itself when both run
        # on the same port — not the case today, but harmless if it ever is.
        "http://127.0.0.1:8800",
        "http://localhost:8800",
    }
)
_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


# Body-size cap (1 MB). Chat prompts shouldn't exceed this; pulls/models/diag
# don't need bodies that large either. Without this, a local script can POST
# a multi-GB body and OOM the backend before Pydantic gets a chance to reject.
_MAX_BODY_BYTES = 1_000_000


class OriginGuard(BaseHTTPMiddleware):
    """Reject mutating cross-origin requests and over-size bodies.

    Backend binds 127.0.0.1, so the threat is a malicious page in another tab
    firing a CORS-simple POST (e.g. `fetch('/api/diagnostic',{method:'POST'})`)
    — the browser sends it without preflight, and even though the response is
    opaque to the attacker, the side effect (spawning subprocesses, pulling
    models) is enough damage. Browsers always send Origin on cross-origin
    POSTs; we allow missing Origin so curl/local scripts still work.

    Also enforces a Content-Length cap on mutating requests — Pydantic's
    field-level max_length runs after the body is buffered, so a multi-GB
    POST would OOM before validation. Reject up front.
    """

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Any:
        if request.method in _MUTATING_METHODS:
            origin = request.headers.get("origin")
            if origin and origin not in _ALLOWED_ORIGINS:
                return JSONResponse({"detail": "origin not allowed"}, status_code=403)
            cl = request.headers.get("content-length")
            if cl is not None:
                try:
                    if int(cl) > _MAX_BODY_BYTES:
                        return JSONResponse({"detail": "request body too large"}, status_code=413)
                except ValueError:
                    return JSONResponse({"detail": "invalid content-length"}, status_code=400)
        return await call_next(request)


class SecurityHeaders(BaseHTTPMiddleware):
    """Defense-in-depth response headers.

    - X-Frame-Options blocks the API and SPA from being iframed (clickjacking).
    - CSP frame-ancestors does the modern equivalent.
    - X-Content-Type-Options stops MIME sniffing.
    - Referrer-Policy keeps URLs (which may contain model names) off any link.
    """

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Any:
        resp = await call_next(request)
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'")
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        return resp


# Disable the FastAPI docs UI by default. They aren't needed at runtime —
# the SPA is the only client — and an exposed /openapi.json lays out every
# endpoint + schema for any local process to enumerate. Set OCTOPUS_DOCS=1
# during local debugging if you need them back.
_DOCS_ENABLED = os.environ.get("OCTOPUS_DOCS") == "1"
app = FastAPI(
    title="Octopus",
    lifespan=lifespan,
    docs_url="/docs" if _DOCS_ENABLED else None,
    redoc_url="/redoc" if _DOCS_ENABLED else None,
    openapi_url="/openapi.json" if _DOCS_ENABLED else None,
)
app.add_middleware(SecurityHeaders)
app.add_middleware(OriginGuard)


class ChatMessage(BaseModel):
    # Caps are generous but defined — without them a single message could be
    # MBs of text, and the request as a whole is body-size-capped anyway.
    role: str
    content: str = Field(..., max_length=200_000)

    @field_validator("role")
    @classmethod
    def _check_role(cls, v: str) -> str:
        if v not in {"user", "assistant", "system"}:
            raise ValueError(f"invalid role: {v!r}")
        return v


class ChatRequest(BaseModel):
    model: str = Field(..., max_length=200)
    messages: list[ChatMessage] = Field(..., max_length=200)

    @field_validator("model")
    @classmethod
    def _check_model(cls, v: str) -> str:
        if not _is_valid_model_name(v):
            raise ValueError("invalid model name")
        return v


class PullRequest(BaseModel):
    model: str = Field(..., max_length=200)

    @field_validator("model")
    @classmethod
    def _check_model(cls, v: str) -> str:
        if not _is_valid_model_name(v):
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
        parts = [p.strip() for p in line.split(",")]
        # Skip malformed lines rather than 500'ing the endpoint — a driver
        # quirk that changes column count shouldn't take down telemetry.
        if len(parts) != 5:
            continue
        try:
            gpus.append(
                {
                    "name": parts[0],
                    "memory_used_mb": int(parts[1]),
                    "memory_total_mb": int(parts[2]),
                    "utilization_pct": int(parts[3]),
                    "temp_c": int(parts[4]),
                }
            )
        except ValueError:
            continue
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
                    # Ollama reports failures (model missing, OOM, …) as an
                    # `{"error": ...}` line with no `message`/`done` — on both
                    # non-200 responses and mid-stream faults. Without this
                    # branch the stream just ends and the UI shows an empty
                    # reply. The text comes from local Ollama and *is* the
                    # fix-it hint ('model "x" not found'), so forward it.
                    if chunk.get("error"):
                        log.warning("ollama chat error: %s", chunk["error"])
                        yield _sse({"type": "error", "message": str(chunk["error"])[:500]})
                        return
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
            # Log full exception server-side; show generic message client-side
            # so OLLAMA_URL and other internals don't leak to the rendered DOM.
            log.warning("chat stream failed: %s", e)
            yield _sse({"type": "error", "message": "upstream unreachable"})

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
                    # Ollama pull failures arrive as a bare `{"error": ...}`
                    # line with no status; normalize to the {"status": "error"}
                    # shape the UI handles so bad model names don't fail silently.
                    if chunk.get("error") and chunk.get("status") != "error":
                        chunk = {"status": "error", "error": str(chunk["error"])[:500]}
                    yield _sse(chunk)
        except httpx.RequestError as e:
            log.warning("pull stream failed: %s", e)
            yield _sse({"status": "error", "error": "upstream unreachable"})

    return StreamingResponse(stream(), media_type="text/event-stream")


# --- Diagnostic ---------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"


_HOME = os.path.expanduser("~")


def _scrub_paths(text: str) -> str:
    """Strip absolute paths from diagnostic output. Avoids leaking the user's
    username (via $HOME) and any repo path that diverges from $CWD when
    rendered into the UI or copied to the clipboard."""
    return text.replace(str(REPO_ROOT), ".").replace(_HOME, "~")


# Resolve diagnostic binaries to absolute paths at import time. Without this
# a malicious shadow `npm` on PATH could be invoked by the diagnostic; with
# it, the path is fixed at process start and re-resolution can't poison it.
_RESOLVED_BINS: dict[str, str] = {}


def _resolve_bin(name: str) -> str:
    if name not in _RESOLVED_BINS:
        path = shutil.which(name)
        # Fall back to the bare name; FileNotFoundError downstream tells the
        # user the binary's missing, which is honest.
        _RESOLVED_BINS[name] = path or name
    return _RESOLVED_BINS[name]


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
        text = _scrub_paths(stdout.decode("utf-8", errors="replace").strip())
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


# Patterns we never want to ship — secrets, debug leftovers. Frontend +
# backend are both scanned; without the backend pass the "all clear" badge
# would mislead about scope. Common token shapes (AWS access key, GitHub
# personal-access token) catch the most-likely accident.
_AUDIT_PATTERNS = [
    (
        re.compile(r"(?i)\b(api[_-]?key|secret|password|bearer\s+[A-Za-z0-9_\-]{16,})\s*[:=]"),
        "possible credential literal",
    ),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36}\b"), "GitHub personal access token"),
    (re.compile(r"console\.log\("), "console.log left in source"),
    (re.compile(r"\bdebugger\b"), "debugger statement"),
]


# Prune massive irrelevant trees at descent time so we never enter them.
# `Path.rglob` + post-filter still walks every node_modules subdir on disk
# (thousands of files per repo); the audit then iterates a giant list. Use
# os.walk so we can mutate dirs[] and skip whole subtrees before they're
# enumerated.
_AUDIT_PRUNE_DIRS = frozenset({"node_modules", ".venv", ".git", "dist", "__pycache__"})


def _walk_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _AUDIT_PRUNE_DIRS]
        for name in filenames:
            if name.endswith(suffixes):
                out.append(Path(dirpath) / name)
    return out


async def _check_audit() -> dict[str, Any]:
    findings: list[str] = []
    targets = (
        _walk_files(FRONTEND_DIR / "src", (".svelte", ".js"))
        + _walk_files(BACKEND_DIR, (".py",))
        + _walk_files(REPO_ROOT, (".sh",))
    )
    # Files that legitimately contain pattern-shaped strings:
    # - test fixtures (`console.log`, stub credentials, etc.)
    # - this file (the audit patterns + their remediation copy)
    # - the matching pre-commit secret-scan script (mirrors the patterns)
    audit_self = (BACKEND_DIR / "main.py").resolve()
    scan_script = (REPO_ROOT / "scripts" / "secret-scan.sh").resolve()
    for path in targets:
        if ".test." in path.name or ".spec." in path.name or path.name == "test_main.py":
            continue
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in (audit_self, scan_script):
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


_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def _parse_version(v: str) -> tuple[int, int, int] | None:
    m = _VERSION_RE.search(v or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


async def _check_ollama_version_update() -> dict[str, Any]:
    """Compare running Ollama against latest GitHub release. Warn → upgrade exists."""
    try:
        r = await client.get("/api/version", timeout=2.0)
        if r.status_code != 200:
            return {"status": "warn", "detail": f"local version HTTP {r.status_code}"}
        local_raw = r.json().get("version", "")
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        return {"status": "warn", "detail": f"could not read local version: {e}"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0), follow_redirects=False) as gh:
            gr = await gh.get("https://api.github.com/repos/ollama/ollama/releases/latest")
    except httpx.RequestError as e:
        log.warning("GitHub unreachable for Ollama version check: %s", e)
        return {"status": "warn", "detail": "GitHub unreachable"}
    if gr.status_code != 200:
        return {"status": "warn", "detail": f"GitHub HTTP {gr.status_code}"}
    latest_raw = gr.json().get("tag_name", "")
    local, latest = _parse_version(local_raw), _parse_version(latest_raw)
    if not local or not latest:
        return {"status": "warn", "detail": f"unparseable versions: {local_raw!r} / {latest_raw!r}"}
    if local >= latest:
        return {"status": "pass", "detail": f"running {local_raw} (latest {latest_raw})"}
    return {"status": "warn", "detail": f"running {local_raw}, latest is {latest_raw}"}


async def _check_ollama_model_updates() -> dict[str, Any]:
    """Compare each pulled model's digest against the Ollama library registry."""
    try:
        r = await client.get("/api/tags", timeout=5.0)
        if r.status_code != 200:
            return {"status": "warn", "detail": f"could not list models (HTTP {r.status_code})"}
        models = r.json().get("models", []) or []
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        return {"status": "warn", "detail": f"could not list models: {e}"}
    if not models:
        return {"status": "pass", "detail": "no models installed"}

    stale: list[str] = []
    checked = 0
    skipped = 0
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0), follow_redirects=False) as reg:
        for m in models:
            name = m.get("name") or m.get("model") or ""
            local_digest = (m.get("digest") or "").lower().removeprefix("sha256:")
            base, _, tag = name.partition(":")
            tag = tag or "latest"
            # Only library/* models can be checked against registry.ollama.ai; user
            # namespaces (foo/bar) and external sources (hf.co/...) are skipped.
            if not name or not local_digest or "/" in base:
                skipped += 1
                continue
            # Quote path segments — Ollama validates model names server-side, but
            # the registry HEAD is defense-in-depth against a malformed name
            # carrying url-special characters.
            url = (
                f"https://registry.ollama.ai/v2/library/{quote(base, safe='')}"
                f"/manifests/{quote(tag, safe='')}"
            )
            try:
                resp = await reg.head(
                    url,
                    headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"},
                )
            except httpx.RequestError:
                skipped += 1
                continue
            if resp.status_code != 200:
                skipped += 1
                continue
            remote = resp.headers.get("docker-content-digest", "").lower().removeprefix("sha256:")
            checked += 1
            if remote and remote != local_digest:
                stale.append(name)
    if not checked:
        return {"status": "warn", "detail": f"no models checkable (skipped {skipped})"}
    if stale:
        pulls = "\n".join(f"  ollama pull {n}" for n in stale)
        return {
            "status": "warn",
            "detail": f"{len(stale)} stale: {', '.join(stale)}",
            "remediation": f"Re-pull each stale model:\n{pulls}",
        }
    return {"status": "pass", "detail": f"all {checked} models up to date"}


def _format_outdated_detail(names: list[str]) -> str:
    head = ", ".join(names[:10])
    tail = f", … (+{len(names) - 10})" if len(names) > 10 else ""
    return f"{len(names)} outdated: {head}{tail}"


async def _check_npm_outdated() -> dict[str, Any]:
    """`npm outdated --json` in frontend/. Empty → pass; populated → warn."""
    try:
        proc = await asyncio.create_subprocess_exec(
            _resolve_bin("npm"),
            "outdated",
            "--json",
            cwd=str(FRONTEND_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return {"status": "warn", "detail": "npm not installed"}
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60.0)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return {"status": "warn", "detail": "npm outdated timed out"}
    text = stdout.decode("utf-8", errors="replace").strip() or "{}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"status": "warn", "detail": "could not parse npm output"}
    if not data:
        return {"status": "pass", "detail": "all npm packages up to date"}
    return {"status": "warn", "detail": _format_outdated_detail(sorted(data.keys()))}


async def _check_pip_outdated() -> dict[str, Any]:
    """`pip list --outdated --format=json` in backend venv. Empty → pass; populated → warn."""
    pip = BACKEND_DIR / ".venv" / "bin" / "pip"
    try:
        proc = await asyncio.create_subprocess_exec(
            str(pip),
            "list",
            "--outdated",
            "--format=json",
            cwd=str(BACKEND_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return {"status": "warn", "detail": "pip not found in backend venv"}
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60.0)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return {"status": "warn", "detail": "pip outdated timed out"}
    text = stdout.decode("utf-8", errors="replace").strip() or "[]"
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"status": "warn", "detail": "could not parse pip output"}
    if not data:
        return {"status": "pass", "detail": "all pip packages up to date"}
    names = sorted(p.get("name", "?") for p in data)
    # Special-case pydantic_core: pinned `==` by pydantic, so a new pydantic_core
    # is uninstallable until pydantic itself releases. Don't tell users to run a
    # command that won't work.
    if names == ["pydantic_core"]:
        remediation = (
            "pydantic_core is hard-pinned by pydantic — it auto-resolves when "
            "pydantic releases a version with a newer pin. No action needed."
        )
    else:
        remediation = (
            "Upgrade transitive deps in the backend venv:\n"
            "  cd backend && .venv/bin/pip install --upgrade --upgrade-strategy eager "
            "-r requirements-dev.txt"
        )
    return {
        "status": "warn",
        "detail": _format_outdated_detail(names),
        "remediation": remediation,
    }


CheckFn = Callable[[], Awaitable[dict[str, Any]]]

# Static remediation text shown when a check is not "pass". Per-check functions
# can override by returning a "remediation" key in their result dict (used when
# the fix depends on the failure detail — e.g., listing specific stale models).
_DEFAULT_REMEDIATIONS: dict[str, str] = {
    "ollama": "Start Ollama:\n  systemctl start ollama\nor:\n  ollama serve",
    "disk": (
        "Free space. Largest typical culprit is the Ollama model store:\n"
        "  du -sh ~/.ollama/models/* 2>/dev/null | sort -h\n"
        "  ollama rm <model>"
    ),
    "backend_lint": ("Auto-fix:\n  cd backend && .venv/bin/ruff check --fix ."),
    "backend_format": ("Auto-fix:\n  cd backend && .venv/bin/ruff format ."),
    "backend_types": "Address the type errors above and re-run.",
    "backend_tests": "Inspect the failing tests above and fix the regression.",
    "frontend_types": "Address the svelte-check errors above and re-run.",
    "frontend_lint": "Auto-fix what can be:\n  cd frontend && npm run lint:fix",
    "frontend_tests": "Inspect the failing vitest output above and fix the regression.",
    "audit": (
        "Remove `console.log`, `debugger`, or credential-shaped literals from the listed files."
    ),
    "ollama_version_update": (
        "Upgrade Ollama:\n"
        "  curl -fsSL https://ollama.com/install.sh | sh\n"
        "  sudo systemctl restart ollama"
    ),
    "npm_outdated": (
        "Bump everything to latest:\n"
        "  cd frontend && npm install --save-dev <pkg>@latest [<pkg>@latest ...]"
    ),
}

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
        lambda: _run_shell([_resolve_bin("npm"), "run", "check"], FRONTEND_DIR),
    ),
    (
        "frontend_lint",
        "frontend · eslint",
        "code",
        lambda: _run_shell([_resolve_bin("npm"), "run", "lint"], FRONTEND_DIR),
    ),
    (
        "frontend_tests",
        "frontend · vitest",
        "code",
        lambda: _run_shell([_resolve_bin("npm"), "run", "test"], FRONTEND_DIR),
    ),
    ("audit", "audit · secrets / debug leftovers", "audit", _check_audit),
    ("ollama_version_update", "Ollama version up to date", "updates", _check_ollama_version_update),
    ("ollama_model_updates", "Ollama models up to date", "updates", _check_ollama_model_updates),
    ("npm_outdated", "npm packages up to date", "updates", _check_npm_outdated),
    ("pip_outdated", "pip packages up to date", "updates", _check_pip_outdated),
]


@app.get("/api/diagnostic/checks")
def diagnostic_checks() -> dict[str, Any]:
    """List the checks the diagnostic will run, so the UI can render them up front."""
    return {
        "checks": [
            {"id": cid, "name": name, "category": cat} for cid, name, cat, _ in _DIAGNOSTIC_CHECKS
        ]
    }


# Single-flight: only one diagnostic run at a time. A page reload or a
# malicious script could otherwise spawn N parallel runs of `npm`,
# `pytest`, `mypy`, etc., saturating disk and CPU.
_diagnostic_lock = asyncio.Lock()


@app.post("/api/diagnostic")
async def run_diagnostic() -> StreamingResponse:
    """Run every diagnostic check, streaming results as each finishes (SSE)."""
    if _diagnostic_lock.locked():
        raise HTTPException(status_code=409, detail="diagnostic already running")

    async def stream() -> AsyncIterator[bytes]:
        async with _diagnostic_lock:
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
                    log.exception("diagnostic check %r raised", cid)
                    result = {"status": "fail", "detail": f"check raised: {type(e).__name__}"}
                ms = int((time.perf_counter() - t0) * 1000)
                status = result.get("status", "fail")
                summary[status] = summary.get(status, 0) + 1
                # Per-check remediation overrides the static default; only attach
                # when the check didn't pass (no point telling the user how to fix
                # something that's working).
                remediation = result.get("remediation") or (
                    _DEFAULT_REMEDIATIONS.get(cid) if status != "pass" else None
                )
                yield _sse(
                    {
                        "type": "check",
                        "id": cid,
                        "name": name,
                        "category": category,
                        "status": status,
                        "duration_ms": ms,
                        "detail": result.get("detail", ""),
                        "remediation": remediation,
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
