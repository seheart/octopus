// Module-scoped pull state, so a download survives navigating away from the
// Install page: the progress bar is still there when you come back, and the
// single-pull guard can't be reset by a remount. (Previously all of this
// lived in PullPage component state — leaving mid-pull orphaned the stream
// and let you start a second concurrent pull.)

import { pullModel } from '../api.js';
import { setModel, selectedModel } from './model.svelte.js';

export const pull = $state({
  name: '',
  active: false,
  status: '',
  pct: null,
  total: null,
  completed: null,
  error: null,
  bytesPerSec: 0,
  // Bumped on each successful install so views can refresh their
  // installed-models list without polling.
  installedVersion: 0
});

/** @type {{ done: Promise<void>, abort: () => void } | null} */
let current = null;
let lastSample = { at: 0, bytes: 0 };

export async function startPull(name) {
  const target = (name || '').trim();
  if (!target || pull.active) return;
  pull.active = true;
  pull.name = target;
  pull.status = 'starting…';
  pull.pct = null;
  pull.total = null;
  pull.completed = null;
  pull.error = null;
  pull.bytesPerSec = 0;
  lastSample = { at: Date.now(), bytes: 0 };

  try {
    current = pullModel(target, (evt) => {
      if (evt.status === 'error') {
        pull.error = evt.error || 'install failed';
        return;
      }
      pull.status = evt.status;
      if (typeof evt.total === 'number') pull.total = evt.total;
      if (typeof evt.completed === 'number') {
        pull.completed = evt.completed;
        if (pull.total) pull.pct = Math.min(100, (pull.completed / pull.total) * 100);
        // Bytes/sec EMA over a ~3s window for ETA smoothing.
        const now = Date.now();
        const dtMs = now - lastSample.at;
        if (dtMs > 300) {
          const inst = ((pull.completed - lastSample.bytes) / dtMs) * 1000;
          pull.bytesPerSec = pull.bytesPerSec ? pull.bytesPerSec * 0.7 + inst * 0.3 : inst;
          lastSample = { at: now, bytes: pull.completed };
        }
      }
    });
    await current.done;
    if (!pull.error) {
      pull.status = 'success';
      pull.installedVersion++;
      if (!selectedModel.value) setModel(target);
    }
  } catch (e) {
    if (e.name !== 'AbortError') pull.error = e.message;
  } finally {
    pull.active = false;
    current = null;
  }
}

export function cancelPull() {
  current?.abort();
}
