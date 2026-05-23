/**
 * modelFit.js — estimate how well an Ollama model will run on this machine.
 *
 * A rough heuristic, not a guarantee: running a model needs roughly its
 * on-disk size plus ~20% for the KV cache and runtime overhead. VRAM means
 * full GPU speed; RAM-only means it still runs, just slower (CPU / offload).
 *
 * Crucially, a model can't claim *all* of RAM — the OS and other apps need
 * their share. Ignoring that is how an 8.15 GB model got classed "tight" on
 * an 8.6 GB machine and froze it. So RAM is discounted by an OS reserve.
 *
 * Pure functions — no I/O, no dependencies — so they're trivially testable
 * and work on any model the curated list grows tomorrow.
 */

const RUN_OVERHEAD = 1.2; // weights + modest KV cache + runtime headroom

/**
 * RAM actually available to a model — total minus what the OS and other
 * apps need to stay responsive (the larger of 20% or 1.5 GB). A model whose
 * footprint exceeds this will swap the machine to a standstill.
 *
 * @param {number} ramBytes
 * @returns {number}
 */
function usableRam(ramBytes) {
  return Math.max(0, ramBytes - Math.max(ramBytes * 0.2, 1.5e9));
}

/**
 * Parse one of PullPage's approximate size strings ("~2 GB", "~270 MB")
 * into bytes. Returns 0 when there's nothing parseable.
 *
 * @param {string} s
 * @returns {number}
 */
export function parseApproxSize(s) {
  const m = /([\d.]+)\s*(GB|MB)/i.exec(s || '');
  if (!m) return 0;
  const n = parseFloat(m[1]);
  return m[2].toUpperCase() === 'GB' ? n * 1e9 : n * 1e6;
}

/**
 * @typedef {Object} Hardware
 * @property {number} [ramBytes] - total system RAM
 * @property {number} [vramBytes] - total GPU VRAM (0 when there's no GPU)
 *
 * @typedef {Object} Fit
 * @property {'great' | 'tight' | 'wont-fit' | 'unknown'} tier
 * @property {string} label - short badge text
 * @property {string} detail - one-line explanation for a tooltip
 */

/**
 * Estimate the fit of a model of the given size against this machine.
 *
 * @param {number} sizeBytes - approximate model size on disk
 * @param {Hardware} [hw]
 * @returns {Fit}
 */
export function modelFit(sizeBytes, hw = {}) {
  const ramBytes = hw.ramBytes || 0;
  const vramBytes = hw.vramBytes || 0;

  // No size, or no hardware data at all — say nothing rather than guess.
  if (!sizeBytes || (!ramBytes && !vramBytes)) {
    return { tier: 'unknown', label: '', detail: '' };
  }

  const footprint = sizeBytes * RUN_OVERHEAD;

  // Comfortably fits in VRAM — the full-GPU-speed path octopus shows off.
  if (vramBytes >= footprint) {
    return {
      tier: 'great',
      label: 'Runs great',
      detail: 'fits in VRAM with headroom — full GPU speed'
    };
  }

  // Needs more memory than the machine can spare — running it would swap
  // the OS to a standstill. This is the freeze case; never offer it.
  const usable = Math.max(vramBytes, usableRam(ramBytes));
  if (footprint > usable) {
    return {
      tier: 'wont-fit',
      label: "Won't fit",
      detail: 'needs more memory than this machine can spare'
    };
  }

  // Loads and runs, but won't get full GPU acceleration.
  return {
    tier: 'tight',
    label: 'Tight',
    detail:
      vramBytes > 0
        ? 'bigger than VRAM — partially offloads to CPU, slower'
        : 'no GPU detected — runs on CPU, slower'
  };
}
