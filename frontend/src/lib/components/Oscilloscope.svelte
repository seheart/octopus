<script>
  import { onMount, onDestroy, untrack } from 'svelte';
  import { SvelteMap, SvelteSet } from 'svelte/reactivity';
  import { colorFor } from './oscilloscope-palette.js';
  import { tokensPerSec } from '../stores/activity.svelte.js';

  /**
   * @type {{ models: Array<{name:string}>, fullScale?: number }}
   * `fullScale` = minimum y-axis range in tokens/sec. The scope auto-scales
   * upward when traffic exceeds this floor, so peaks never clip — the
   * floor just keeps a quiet chart from showing ambient noise as full-height.
   */
  const { models = [], fullScale = 300 } = $props();

  const W = 600;
  const H = 200;
  const SAMPLES = 240; // ~4 seconds of history at 60fps

  // EMA softens raw token-rate jitter so the line flows instead of stutters.
  const EMA_ALPHA = 0.08;

  // Auto-scaling: chart's y-axis max eases toward observed peak (with 10%
  // headroom) so traces never clip but stay relatively stable across spikes.
  const SCALE_ALPHA = 0.05;
  const SCALE_HEADROOM = 1.1;

  // Bidirectional ambient flow — a small traveling sine kept on top of the
  // value so an idle trace still breathes and a saturated trace still bobs.
  const AMBIENT_AMP = 0.06;
  const AMBIENT_WAVELENGTH = 36;
  const PHASE_PER_FRAME = 0.012; // ≈0.7 Hz

  // 5-tap Gaussian applied 4× (≈σ 2) melts any single-sample bumps so the
  // Catmull-Rom spline doesn't cusp where slopes reverse.
  const GAUSS_KERNEL = [1, 4, 6, 4, 1];
  const GAUSS_SUM = 16;
  const SMOOTH_PASSES = 4;

  /** @type {SvelteMap<string, number[]>} per-model EMA-smoothed raw-tps buffer */
  const emaBufs = new SvelteMap();
  /** Models we've ever seen this session — never dropped so the trace
   *  survives Ollama swapping a model out of VRAM. */
  const seen = new SvelteSet();
  // dynamicScale & scaleLabel start at the floor and adapt at runtime; the
  // initial snapshot captures the prop value without reactive subscription.
  const _initialScale = untrack(() => fullScale);
  let phase = 0;
  let dynamicScale = _initialScale;
  let traces = $state([]);
  let scaleLabel = $state(_initialScale);
  /** @type {number | undefined} */
  let raf;

  function gaussSmoothOnce(buf) {
    const n = buf.length;
    const out = new Array(n);
    for (let i = 0; i < n; i++) {
      let s = 0;
      for (let j = -2; j <= 2; j++) {
        const idx = Math.max(0, Math.min(n - 1, i + j));
        s += buf[idx] * GAUSS_KERNEL[j + 2];
      }
      out[i] = s / GAUSS_SUM;
    }
    return out;
  }
  function preSmooth(buf) {
    let out = buf;
    for (let i = 0; i < SMOOTH_PASSES; i++) out = gaussSmoothOnce(out);
    return out;
  }

  function withFlow(v, i, ph) {
    const ambient = AMBIENT_AMP * 0.5 * Math.sin(2 * Math.PI * (i / AMBIENT_WAVELENGTH - ph));
    return Math.max(0, Math.min(1, v + ambient));
  }

  const TOP = 8;
  const BOTTOM = H - 8;
  const STEP = W / (SAMPLES - 1);

  /** Catmull-Rom → cubic bezier on a pre-smoothed buffer. */
  function smoothLine(buf, ph) {
    if (buf.length < 2) return '';
    const s = preSmooth(buf);
    const pts = s.map((v, i) => [i * STEP, BOTTOM - withFlow(v, i, ph) * (BOTTOM - TOP)]);
    let d = `M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = pts[Math.min(pts.length - 1, i + 2)];
      const c1x = (p1[0] + (p2[0] - p0[0]) / 6).toFixed(1);
      const c1y = (p1[1] + (p2[1] - p0[1]) / 6).toFixed(1);
      const c2x = (p2[0] - (p3[0] - p1[0]) / 6).toFixed(1);
      const c2y = (p2[1] - (p3[1] - p1[1]) / 6).toFixed(1);
      d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
    }
    return d;
  }

  function frame() {
    phase = (phase + PHASE_PER_FRAME) % 1;

    // Add any newly-loaded models to the seen set; never drop.
    for (const m of models) seen.add(m.name);

    // Update each ever-seen model's EMA buffer in raw tok/s. Models that
    // aren't currently loaded just sample 0 and flatline.
    let observedPeak = 0;
    for (const name of seen) {
      const tps = tokensPerSec(name);
      let ema = emaBufs.get(name);
      if (!ema) {
        ema = new Array(SAMPLES).fill(tps);
        emaBufs.set(name, ema);
      }
      const last = ema[ema.length - 1] ?? 0;
      const nextEma = last + EMA_ALPHA * (tps - last);
      ema.push(nextEma);
      ema.shift();
      if (nextEma > observedPeak) observedPeak = nextEma;
    }

    // Auto-scale y-axis: ease dynamicScale toward observedPeak (with
    // headroom), floored at the fullScale prop so a quiet chart stays calm.
    const target = Math.max(fullScale, observedPeak * SCALE_HEADROOM);
    dynamicScale = dynamicScale + SCALE_ALPHA * (target - dynamicScale);

    // Build normalized paths for every seen model.
    const next = [];
    for (const name of seen) {
      const ema = emaBufs.get(name) ?? new Array(SAMPLES).fill(0);
      const normalized = ema.map((v) => Math.min(1, v / dynamicScale));
      next.push({
        name,
        color: colorFor(name),
        tps: tokensPerSec(name),
        d: smoothLine(normalized, phase)
      });
    }
    traces = next;
    scaleLabel = dynamicScale;
    raf = requestAnimationFrame(frame);
  }

  onMount(() => {
    raf = requestAnimationFrame(frame);
  });
  onDestroy(() => {
    if (raf !== undefined) cancelAnimationFrame(raf);
  });
</script>

<div class="rounded-lg p-3 flex flex-col h-full min-h-0" style="background: var(--scope-bg)">
  <div class="relative flex-1 min-h-0">
    <svg
      viewBox="0 0 {W} {H}"
      class="absolute inset-0 w-full h-full"
      preserveAspectRatio="none"
      role="img"
      aria-label="Per-model tokens per second"
    >
      <defs>
        <pattern id="osc-grid" width="30" height="22" patternUnits="userSpaceOnUse">
          <path
            d="M 30 0 L 0 0 0 22"
            fill="none"
            stroke-width="0.5"
            style="stroke: var(--scope-grid)"
          />
        </pattern>
        <filter id="osc-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width={W} height={H} fill="url(#osc-grid)" />
      <!-- Baseline (idle = 0 tok/s) -->
      <line
        x1="0"
        y1={H - 8}
        x2={W}
        y2={H - 8}
        stroke-width="0.8"
        style="stroke: var(--scope-grid)"
      />
      <!-- Full-scale guide -->
      <line
        x1="0"
        y1="8"
        x2={W}
        y2="8"
        stroke-width="0.4"
        stroke-dasharray="2 4"
        style="stroke: var(--scope-grid)"
      />
      {#each traces as tr (tr.name)}
        <path
          d={tr.d}
          fill="none"
          stroke-width="1.8"
          filter="url(#osc-glow)"
          style="stroke: {tr.color}"
        />
      {/each}
    </svg>
    <!-- Axis labels in HTML so they aren't stretched by preserveAspectRatio="none" -->
    <span
      class="absolute left-1.5 top-1 text-[10px] font-mono pointer-events-none"
      style="color: var(--scope-axis-label)"
    >
      {scaleLabel.toFixed(0)} tok/s
    </span>
    <span
      class="absolute left-1.5 bottom-1 text-[10px] font-mono pointer-events-none"
      style="color: var(--scope-axis-label)"
    >
      0 tok/s
    </span>
  </div>
  <div class="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[10px] font-mono">
    {#each traces as tr (tr.name)}
      <span class="flex items-center gap-1.5" style="color: {tr.color}">
        <span class="w-2 h-2 rounded-full inline-block" style="background: {tr.color}"></span>
        {tr.name}
        <span class="opacity-70">· {tr.tps.toFixed(1)} tok/s</span>
      </span>
    {/each}
    {#if traces.length === 0}
      <span class="text-muted">no models loaded</span>
    {/if}
  </div>
</div>
