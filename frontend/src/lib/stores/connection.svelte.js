// Tracks reachability of the two things that can be down independently:
// the FastAPI backend, and Ollama itself. Keeping them separate lets the
// app tell the user the *right* thing to fix — a fresh install with the
// backend running but `ollama serve` not started is the common case, and
// must not be reported as "backend unreachable".
//
// The Footer poller is the sole writer; pages read but shouldn't write.

export const connection = $state({
  backend: true, // FastAPI on :8800 reachable
  ollama: true, // `ollama serve` reachable (only meaningful when backend is up)
  // Counts consecutive failures so we don't flash on a single hiccup.
  failureCount: 0
});

/**
 * Record a successful poll. The backend is up by definition (we got a
 * response); `ollamaReachable` carries whether Ollama answered too.
 * @param {boolean} ollamaReachable
 */
export function markOk(ollamaReachable = true) {
  connection.backend = true;
  connection.ollama = ollamaReachable;
  connection.failureCount = 0;
}

/** Record a failed poll — the backend itself didn't answer. */
export function markFail() {
  connection.failureCount += 1;
  // Only flip "down" after 2 consecutive failures (~10s).
  if (connection.failureCount >= 2) connection.backend = false;
}
