#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

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
