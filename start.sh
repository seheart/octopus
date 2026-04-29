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
wait
