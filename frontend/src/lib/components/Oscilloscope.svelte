<script>
  import { onMount, onDestroy } from 'svelte';
  import { SvelteMap } from 'svelte/reactivity';
  import { colorFor } from './oscilloscope-palette.js';
  import { tokensPerSec } from '../stores/activity.svelte.js';

  /**
   * @type {{ models: Array<{name:string}>, fullScale?: number }}
   * `fullScale` = tokens/sec that maps to the top of the trace. Anything
   * higher saturates at the top. Default is a generous 80 tok/s.
   */
  const { models = [], fullScale = 80 } = $props();

  const W = 600;
  const H = 220;
  const SAMPLES = 240; // ~4 seconds of history at 60fps

  /** @type {SvelteMap<string, number[]>} per-model rolling sample buffer */
  const buffers = new SvelteMap();
  let traces = $state([]);
  /** @type {number | undefined} */
  let raf;

  function frame() {
    const next = [];
    for (const m of models) {
      let buf = buffers.get(m.name);
      if (!buf) {
        buf = new Array(SAMPLES).fill(0);
        buffers.set(m.name, buf);
      }
      // Real measurement — tokens/sec averaged over the activity store's
      // window. Returns 0 when the model isn't generating; rises when it is.
      const tps = tokensPerSec(m.name);
      const v = Math.min(1, tps / fullScale);
      buf.push(v);
      if (buf.length > SAMPLES) buf.shift();

      // Plot: idle = baseline at the bottom; active = trace pushes up.
      // 8px margins so the line never hits the edge.
      const top = 8;
      const bottom = H - 8;
      const step = W / (SAMPLES - 1);
      let d = '';
      for (let i = 0; i < buf.length; i++) {
        const x = i * step;
        const y = bottom - buf[i] * (bottom - top);
        d += (i === 0 ? 'M' : 'L') + x.toFixed(1) + ' ' + y.toFixed(1) + ' ';
      }
      next.push({ name: m.name, color: colorFor(m.name), d, tps });
    }
    traces = next;
    raf = requestAnimationFrame(frame);
  }

  onMount(() => {
    raf = requestAnimationFrame(frame);
  });
  onDestroy(() => {
    if (raf !== undefined) cancelAnimationFrame(raf);
  });
</script>

<div class="rounded-lg p-3" style="background: var(--scope-bg)">
  <svg
    viewBox="0 0 {W} {H}"
    class="w-full h-auto"
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
    <text
      x="4"
      y="14"
      font-family="ui-monospace, monospace"
      font-size="9"
      style="fill: var(--scope-axis-label)"
    >
      {fullScale} tok/s
    </text>
    <text
      x="4"
      y={H - 12}
      font-family="ui-monospace, monospace"
      font-size="9"
      style="fill: var(--scope-axis-label)"
    >
      0 tok/s
    </text>
    {#each traces as tr (tr.name)}
      <path
        d={tr.d}
        fill="none"
        stroke-width="1.4"
        filter="url(#osc-glow)"
        style="stroke: {tr.color}"
      />
    {/each}
  </svg>
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
