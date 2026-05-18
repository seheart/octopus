#!/usr/bin/env bash
# Round-robin: one /api/generate request at a time, cycling through models.
# Sequential (not concurrent) so Ollama can swap models cleanly without
# fighting itself. Each request asks for keep_alive=10m so once a model
# has had its turn, it stays warm in VRAM if there's room.
#
# Defaults to real Ollama (127.0.0.1:11435) rather than the proxy on 11434
# (which rate-limits to ~10 inference req/min). Override with OLLAMA_HOST.
#
# Usage: ./scripts/multi-model-loop.sh [model …]

set -u

HOST=${OLLAMA_HOST:-http://127.0.0.1:11435}

if [ "$#" -gt 0 ]; then
  MODELS=("$@")
else
  MODELS=(
    "llama3.1:8b"
    "qwen2.5-coder:7b-instruct-q5_K_M"
    "qwen2.5-coder:14b"
    "qwen3:14b"
  )
fi

PROMPTS=(
  "Say one short sentence about clouds."
  "Name a kitchen utensil."
  "Reply with exactly five words."
  "Give one fact about octopuses."
  "Write a single haiku."
  "Count: one two three…"
  "Translate 'hello' to Japanese."
  "Pick any color, just say its name."
)

# Echo the model list once at startup so the operator can see what's running.
echo "round-robin loop against $HOST"
for m in "${MODELS[@]}"; do echo "  · $m"; done
echo "Ctrl-C to stop."

current_curl_pid=""
cleanup() {
  echo
  echo "stopping…"
  [ -n "$current_curl_pid" ] && kill -9 "$current_curl_pid" 2>/dev/null
  exit 0
}
trap cleanup INT TERM

i=0
while :; do
  m="${MODELS[$((i % ${#MODELS[@]}))]}"
  p="${PROMPTS[$((RANDOM % ${#PROMPTS[@]}))]}"
  body=$(python3 -c '
import json, sys
print(json.dumps({
  "model": sys.argv[1],
  "prompt": sys.argv[2],
  "stream": True,
  "keep_alive": "10m",
}))
' "$m" "$p")
  curl -sN "$HOST/api/generate" \
    -H 'Content-Type: application/json' \
    -d "$body" >/dev/null 2>&1 &
  current_curl_pid=$!
  wait "$current_curl_pid"
  current_curl_pid=""
  i=$((i + 1))
done
