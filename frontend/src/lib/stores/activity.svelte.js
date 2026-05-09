// Per-model live activity, populated by the chat stream as tokens arrive.
// Read by the Oscilloscope every animation frame to plot a real signal:
// idle models flatline at zero; active models rise with their real
// tokens-per-second.
//
// Not reactive on purpose — consumers (the Oscilloscope) sample on rAF,
// so we'd just churn Svelte's reactivity for nothing.

import { SvelteMap } from 'svelte/reactivity';

// Smoothing window. Shorter = more jitter (more "scope"-ish), longer =
// steadier. ~500ms feels honest: you see each token contribute, but a
// single late token doesn't tank the reading.
const WINDOW_MS = 500;

/** @type {SvelteMap<string, number[]>} per-model token-arrival timestamps (ms). */
const tokenTimes = new SvelteMap();

/** Record one output token for a model. Called from the chat SSE loop. */
export function recordToken(modelName) {
  if (!modelName) return;
  let arr = tokenTimes.get(modelName);
  if (!arr) {
    arr = [];
    tokenTimes.set(modelName, arr);
  }
  arr.push(performance.now());
  // Bound the buffer so a long conversation doesn't grow it forever.
  if (arr.length > 4096) arr.splice(0, arr.length - 2048);
}

/**
 * Tokens-per-second over the last WINDOW_MS for a given model.
 * Returns 0 if the model has no recent tokens — i.e. truly idle.
 */
export function tokensPerSec(modelName) {
  const arr = tokenTimes.get(modelName);
  if (!arr || arr.length === 0) return 0;
  const now = performance.now();
  // Prune in place. Cheap because we only ever append, so the array is
  // sorted and we can drop from the front.
  while (arr.length && arr[0] < now - WINDOW_MS) arr.shift();
  return arr.length * (1000 / WINDOW_MS);
}
