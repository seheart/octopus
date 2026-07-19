// Per-model live activity. Two sources feed it:
//   1. recordToken — exact, called from Octopus's own chat SSE loop on
//      every token. True tokens/sec.
//   2. recordPulse — heuristic, fired by the poller below when ANY Ollama
//      client (raven, ollama CLI, Claude Code, another app) touches a
//      model. We can't see external tokens, but Ollama's expires_at
//      advances on every request, so a rising expires_at == "model was
//      just used." We translate that into a brief synthetic burst so the
//      trace spikes on the scope.
//
// Read by the Oscilloscope on every animation frame.

import { SvelteMap, SvelteSet } from 'svelte/reactivity';
import { getLoaded } from '../api.js';

// Smoothing window for tokensPerSec.
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
  if (arr.length > 4096) arr.splice(0, arr.length - 2048);
}

/**
 * Heuristic activity pulse — used when we *know* a model was touched but
 * don't have per-token granularity (e.g. an external Ollama client).
 * Injects ~25 synthetic tokens spread over 120ms so the scope shows a
 * visible bump that decays naturally as the window slides forward.
 */
const PULSE_COUNT = 25;
const PULSE_SPAN_MS = 120;
function recordPulse(modelName) {
  if (!modelName) return;
  let arr = tokenTimes.get(modelName);
  if (!arr) {
    arr = [];
    tokenTimes.set(modelName, arr);
  }
  const now = performance.now();
  // Spread the synthetic timestamps backward in time so they all start
  // inside the window and age out one by one.
  for (let i = 0; i < PULSE_COUNT; i++) {
    arr.push(now - (i * PULSE_SPAN_MS) / PULSE_COUNT);
  }
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
  while (arr.length && arr[0] < now - WINDOW_MS) arr.shift();
  return arr.length * (1000 / WINDOW_MS);
}

// --- System-wide activity poller --------------------------------------------
// Watches /api/loaded for every client's activity, not just Octopus's chat.
// Reference-counted: the 250ms tick only runs while at least one consumer
// (an Oscilloscope) is on screen — otherwise every open tab hammers the
// backend 4×/second forever for data nothing is rendering.

const POLL_MS = 250;
/** @type {SvelteMap<string, number>} model -> last-seen expires_at (epoch ms) */
const lastExpires = new SvelteMap();
/** @type {ReturnType<typeof setInterval> | undefined} */
let pollHandle;

async function pollOnce() {
  let loaded;
  try {
    loaded = await getLoaded();
  } catch {
    return; // backend down, just skip this tick
  }
  const seen = new SvelteSet();
  for (const m of loaded) {
    seen.add(m.name);
    const exp = m.expires_at ? new Date(m.expires_at).getTime() : 0;
    if (!exp) continue;
    const prev = lastExpires.get(m.name);
    // First-seen models don't pulse — we have no baseline to compare against.
    // Subsequent polls fire a pulse whenever the expiry has advanced, which
    // means Ollama bumped it (a request hit this model since the last poll).
    if (prev !== undefined && exp > prev) {
      recordPulse(m.name);
    }
    lastExpires.set(m.name, exp);
  }
  // Drop tracking for models that have been unloaded.
  for (const name of [...lastExpires.keys()]) {
    if (!seen.has(name)) lastExpires.delete(name);
  }
}

let refCount = 0;

/**
 * Acquire the activity poller. Starts it on the first acquisition; returns a
 * release function that stops it when the last consumer lets go. Call from a
 * component's onMount and invoke the release in its cleanup.
 */
export function acquireActivityPoller() {
  refCount++;
  if (!pollHandle) {
    pollOnce();
    pollHandle = setInterval(pollOnce, POLL_MS);
  }
  let released = false;
  return () => {
    if (released) return; // double-release must not steal another consumer's ref
    released = true;
    refCount = Math.max(0, refCount - 1);
    if (refCount === 0 && pollHandle) {
      clearInterval(pollHandle);
      pollHandle = undefined;
      // Drop expiry baselines — after a gap they'd be stale and the first
      // poll after re-acquire would mis-fire pulses for every loaded model.
      lastExpires.clear();
    }
  };
}
