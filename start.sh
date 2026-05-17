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

# Open browser once frontend is reachable
(
  until curl -sf http://127.0.0.1:8801 >/dev/null 2>&1; do sleep 0.3; done
  command -v xdg-open >/dev/null && xdg-open http://127.0.0.1:8801 >/dev/null 2>&1 || true
) &

wait
