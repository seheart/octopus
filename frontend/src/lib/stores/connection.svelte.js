// Tracks Ollama/backend reachability so the app can surface a banner.
// Footer poller updates this; pages can read but shouldn't write.

export const connection = $state({
  ok: true,
  // Counts consecutive failures so we don't flash on a single hiccup.
  failureCount: 0
});

export function markOk() {
  connection.ok = true;
  connection.failureCount = 0;
}

export function markFail() {
  connection.failureCount += 1;
  // Only flip "down" after 2 consecutive failures (~10s).
  if (connection.failureCount >= 2) connection.ok = false;
}
