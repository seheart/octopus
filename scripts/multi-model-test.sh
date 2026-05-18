#!/usr/bin/env bash
# Fires concurrent /api/generate streams to a few Ollama models so the
# Oscilloscope (Octopus's "live activity" view) shows several traces at
# once. Each request streams tokens; output is discarded — the point is
# that Ollama's expires_at advances, and the activity poller turns each
# touch into a pulse on the scope.

set -u

HOST=${OLLAMA_HOST:-http://127.0.0.1:11434}

# Pick 3 models that comfortably co-exist in VRAM. Override by passing
# model names as arguments: ./scripts/multi-model-test.sh llama3.1:8b qwen3:14b
if [ "$#" -gt 0 ]; then
  MODELS=("$@")
else
  MODELS=(
    "llama3.1:8b"
    "qwen2.5-coder:7b-instruct-q5_K_M"
    "qwen2.5-coder:14b"
  )
fi

# Prompts long enough to keep each stream running ~10–30s.
PROMPTS=(
  "Write a 200-word short story about a deep-sea cable that began to sing."
  "Explain how an oscilloscope phosphor trace works, step by step."
  "List 15 specific ideas for a hobby project involving local LLMs and tiny hardware."
  "Describe the dawn in a city of brass towers, paragraph by paragraph."
  "Walk through, in detail, what happens inside a CPU when you press a key."
)

pids=()
for i in "${!MODELS[@]}"; do
  m="${MODELS[$i]}"
  p="${PROMPTS[$((i % ${#PROMPTS[@]}))]}"
  echo "→ $m"
  curl -sN "$HOST/api/generate" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"$m\",\"prompt\":$(printf '%s' "$p" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),\"stream\":true}" \
    >/dev/null &
  pids+=($!)
done

# Clean shutdown if user Ctrl-C's: kill all curls.
trap 'echo; echo "interrupted — killing in-flight streams"; kill "${pids[@]}" 2>/dev/null; exit 130' INT TERM

echo "watching ${#pids[@]} concurrent streams… (Ctrl-C to stop early)"
wait
echo "✓ all streams finished"
