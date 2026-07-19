#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# Resolve Ollama URL. Honor $OLLAMA_URL, then $OLLAMA_HOST (the ollama-CLI
# convention), then the systemd unit's Environment=, then probe the two
# common ports. Exported so the backend's httpx client points at the right
# place — otherwise the user gets a 500 on /api/models with no hint why.
resolve_ollama_url() {
  if [ -n "$OLLAMA_URL" ]; then echo "$OLLAMA_URL"; return; fi
  if [ -n "$OLLAMA_HOST" ]; then
    case "$OLLAMA_HOST" in http://*|https://*) echo "$OLLAMA_HOST" ;;
    *) echo "http://$OLLAMA_HOST" ;; esac
    return
  fi
  local h
  h=$(systemctl show -p Environment ollama 2>/dev/null | tr ' ' '\n' | sed -n 's/^OLLAMA_HOST=//p' | head -1)
  if [ -n "$h" ]; then echo "http://$h"; return; fi
  for port in 11434 11435; do
    if curl -sf "http://127.0.0.1:$port/api/version" >/dev/null 2>&1; then
      echo "http://127.0.0.1:$port"; return
    fi
  done
  echo "http://127.0.0.1:11434"
}

OLLAMA_URL=$(resolve_ollama_url)
# `0.0.0.0` / `[::]` are *listen* addresses, not connectable ones — typical
# when the systemd unit sets OLLAMA_HOST=0.0.0.0:PORT. Rewrite to loopback so
# the probe below and the backend actually reach the daemon.
# (backend/main.py applies the same rewrite for direct uvicorn runs.)
OLLAMA_URL=$(printf '%s' "$OLLAMA_URL" | sed -e 's|//0\.0\.0\.0|//127.0.0.1|' -e 's|//\[::\]|//[::1]|')
export OLLAMA_URL

if ! curl -sf "$OLLAMA_URL/api/version" >/dev/null 2>&1; then
  echo "Octopus: Ollama not reachable at $OLLAMA_URL" >&2
  echo "  Start it with: systemctl start ollama   (or: ollama serve)" >&2
  echo "  Or set OLLAMA_URL / OLLAMA_HOST to point at your instance." >&2
  exit 1
fi
echo "Octopus: Ollama OK at $OLLAMA_URL"

# Backend
if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q -r backend/requirements-dev.txt
fi

# Frontend
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi

# Run both
trap 'kill 0' EXIT
backend/.venv/bin/uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8800 &
(cd frontend && npm run dev) &

# Open browser once both backend and frontend are reachable. Waiting on
# the backend too avoids the first page load firing API calls before
# uvicorn has finished starting (which produced a spinner-of-doom on slow
# venv initialization).
(
  until curl -sf http://127.0.0.1:8800/api/host >/dev/null 2>&1 \
     && curl -sf http://127.0.0.1:8801 >/dev/null 2>&1; do
    sleep 0.3
  done
  command -v xdg-open >/dev/null && xdg-open http://127.0.0.1:8801 >/dev/null 2>&1 || true
) &

wait
