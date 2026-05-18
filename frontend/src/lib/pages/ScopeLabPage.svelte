<script>
  import { onMount, onDestroy } from 'svelte';
  import { Card, Section } from '../components/ui/index.js';
  import { tokensPerSec } from '../stores/activity.svelte.js';
  import { colorFor } from '../components/oscilloscope-palette.js';
  import { getLoaded } from '../api.js';
  import { go } from '../stores/route.svelte.js';

  const W = 600;
  const H = 180;
  const SAMPLES = 240;
  const FULL_SCALE = 80;
  const EMA_ALPHA = 0.08; // heavier = smoother, more "flow"
  const POLL_MS = 1000;

  let loaded = $state([]);
  let snapshot = $state({ models: [], frame: 0 });
  /** @type {number | undefined} */ let rafId;
  /** @type {ReturnType<typeof setInterval> | undefined} */ let pollId;

  /** @type {Map<string, number[]>} */ const rawBufs = new Map();
  /** @type {Map<string, number[]>} */ const emaBufs = new Map();

  function tick() {
    for (const m of loaded) {
      if (!rawBufs.has(m.name)) {
        rawBufs.set(m.name, new Array(SAMPLES).fill(0));
        emaBufs.set(m.name, new Array(SAMPLES).fill(0));
      }
      const raw = /** @type {number[]} */ (rawBufs.get(m.name));
      const ema = /** @type {number[]} */ (emaBufs.get(m.name));
      const v = Math.min(1, tokensPerSec(m.name) / FULL_SCALE);
      raw.push(v);
      raw.shift();
      const last = ema[ema.length - 1] ?? 0;
      ema.push(last + EMA_ALPHA * (v - last));
      ema.shift();
    }
    snapshot = {
      models: loaded.map((m) => {
        const ema = emaBufs.get(m.name) ?? new Array(SAMPLES).fill(0);
        return {
          name: m.name,
          color: colorFor(m.name),
          raw: rawBufs.get(m.name) ?? new Array(SAMPLES).fill(0),
          ema,
          tps: tokensPerSec(m.name),
          live: ema[ema.length - 1] ?? 0
        };
      }),
      frame: snapshot.frame + 1
    };
    rafId = requestAnimationFrame(tick);
  }

  async function pollLoaded() {
    try {
      loaded = await getLoaded();
    } catch {
      /* backend down, skip */
    }
  }

  onMount(() => {
    pollLoaded();
    pollId = setInterval(pollLoaded, POLL_MS);
    rafId = requestAnimationFrame(tick);
  });
  onDestroy(() => {
    if (rafId !== undefined) cancelAnimationFrame(rafId);
    if (pollId !== undefined) clearInterval(pollId);
  });

  // ---- shared geometry --------------------------------------------------
  const TOP = 8;
  const BOTTOM = H - 8;
  const STEP = W / (SAMPLES - 1);

  // ---- path builders ----------------------------------------------------
  /** Hard line — what the existing scope uses. Sharp verticals, "heartbeat" look. */
  function hardLine(buf) {
    let d = '';
    for (let i = 0; i < buf.length; i++) {
      const x = i * STEP;
      const y = BOTTOM - buf[i] * (BOTTOM - TOP);
      d += (i === 0 ? 'M' : 'L') + x.toFixed(1) + ' ' + y.toFixed(1) + ' ';
    }
    return d;
  }

  /** Catmull-Rom → cubic bezier. Smooth, flowing curves. */
  function smoothLine(buf) {
    if (buf.length < 2) return '';
    const pts = buf.map((v, i) => [i * STEP, BOTTOM - v * (BOTTOM - TOP)]);
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

  /** Smoothed line, closed down to baseline → fillable area. */
  function smoothArea(buf) {
    return smoothLine(buf) + ` L ${W} ${BOTTOM} L 0 ${BOTTOM} Z`;
  }

  /** Mirrored ribbon: smooth band centered on H/2, expanding with intensity. */
  function ribbonBand(buf) {
    if (buf.length < 2) return '';
    const centerY = H / 2;
    const halfH = (H - 16) / 2;
    const topPts = buf.map((v, i) => [i * STEP, centerY - v * halfH]);
    const botPts = buf.map((v, i) => [i * STEP, centerY + v * halfH]);

    function bez(pts) {
      let s = '';
      for (let i = 0; i < pts.length - 1; i++) {
        const p0 = pts[Math.max(0, i - 1)];
        const p1 = pts[i];
        const p2 = pts[i + 1];
        const p3 = pts[Math.min(pts.length - 1, i + 2)];
        const c1x = (p1[0] + (p2[0] - p0[0]) / 6).toFixed(1);
        const c1y = (p1[1] + (p2[1] - p0[1]) / 6).toFixed(1);
        const c2x = (p2[0] - (p3[0] - p1[0]) / 6).toFixed(1);
        const c2y = (p2[1] - (p3[1] - p1[1]) / 6).toFixed(1);
        s += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
      }
      return s;
    }
    let d = `M ${topPts[0][0].toFixed(1)} ${topPts[0][1].toFixed(1)}`;
    d += bez(topPts);
    const last = botPts[botPts.length - 1];
    d += ` L ${last[0].toFixed(1)} ${last[1].toFixed(1)}`;
    d += bez([...botPts].reverse());
    d += ' Z';
    return d;
  }

  /** Comet trail: last N ema samples as fading dots. */
  function particles(buf) {
    const N = 40;
    const start = Math.max(0, buf.length - N);
    const out = [];
    for (let i = start; i < buf.length; i++) {
      const age = (buf.length - 1 - i) / Math.max(1, N - 1); // 0 newest → 1 oldest
      const x = ((i - start) / Math.max(1, N - 1)) * W;
      const y = BOTTOM - buf[i] * (BOTTOM - TOP);
      out.push({ x, y, opacity: 1 - age, r: 1.5 + buf[i] * 6 });
    }
    return out;
  }

  const variants = [
    {
      key: 'heartbeat',
      label: 'heartbeat',
      desc: 'current production scope — raw line on hard verticals; spiky by design.'
    },
    {
      key: 'smooth-wave',
      label: 'smooth wave',
      desc: 'EMA-smoothed samples plotted as a Catmull-Rom curve, filled below with a fade.'
    },
    {
      key: 'ribbon',
      label: 'mirror ribbon',
      desc: 'symmetrical band around a horizontal axis — widens with intensity, like a soundwave.'
    },
    {
      key: 'particles',
      label: 'comet trail',
      desc: 'last 40 samples plotted as fading dots — newest bright, oldest dim.'
    },
    {
      key: 'halo',
      label: 'halo pulse',
      desc: 'no time axis; one circle per model whose radius and opacity track current intensity.'
    }
  ];
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-5xl mx-auto space-y-6">
    <div>
      <div class="flex items-baseline justify-between gap-4 mb-1">
        <h1 class="text-2xl font-bold text-heading">Scope Lab</h1>
        <button
          onclick={() => go('labs')}
          class="bg-transparent border-0 p-0 cursor-pointer font-mono text-xs text-muted hover:text-accent transition-colors"
        >
          ← labs
        </button>
      </div>
      <p class="text-sm text-muted">
        Five visualizations driven by the same live token-rate stream — the existing heartbeat,
        plus four flowing alternatives. Run
        <code class="font-mono text-heading">scripts/multi-model-test.sh</code> in another shell
        to populate the traces.
      </p>
      {#if snapshot.models.length === 0}
        <p class="text-xs font-mono text-muted mt-2">
          · no models loaded — start a chat or fire the test script ·
        </p>
      {/if}
    </div>

    {#each variants as v (v.key)}
      <Card padding="lg">
        <Section title={v.label}>
          <p class="text-xs font-mono text-muted mb-3">{v.desc}</p>
          <div class="rounded-lg overflow-hidden" style="background: var(--scope-bg);">
            <svg
              viewBox="0 0 {W} {H}"
              class="block w-full"
              preserveAspectRatio="none"
              style="height: 180px;"
              role="img"
              aria-label="{v.label} scope"
            >
              <defs>
                <pattern id="sl-grid-{v.key}" width="30" height="22" patternUnits="userSpaceOnUse">
                  <path
                    d="M 30 0 L 0 0 0 22"
                    fill="none"
                    stroke-width="0.5"
                    style="stroke: var(--scope-grid);"
                  />
                </pattern>
                <filter id="sl-glow-{v.key}" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="2" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                {#each snapshot.models as m (m.name + '-' + v.key)}
                  <linearGradient
                    id="sl-area-{v.key}-{m.name}"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="0%" stop-color={m.color} stop-opacity="0.55" />
                    <stop offset="100%" stop-color={m.color} stop-opacity="0" />
                  </linearGradient>
                  <radialGradient id="sl-halo-{v.key}-{m.name}" cx="0.5" cy="0.5" r="0.5">
                    <stop offset="0%" stop-color={m.color} stop-opacity="0.95" />
                    <stop offset="60%" stop-color={m.color} stop-opacity="0.35" />
                    <stop offset="100%" stop-color={m.color} stop-opacity="0" />
                  </radialGradient>
                {/each}
              </defs>
              <rect width={W} height={H} fill="url(#sl-grid-{v.key})" />

              {#if v.key === 'heartbeat'}
                <line
                  x1="0"
                  y1={BOTTOM}
                  x2={W}
                  y2={BOTTOM}
                  stroke-width="0.8"
                  style="stroke: var(--scope-grid);"
                />
                {#each snapshot.models as m (m.name)}
                  <path
                    d={hardLine(m.raw)}
                    fill="none"
                    stroke-width="1.4"
                    filter="url(#sl-glow-{v.key})"
                    style="stroke: {m.color};"
                  />
                {/each}
              {:else if v.key === 'smooth-wave'}
                <line
                  x1="0"
                  y1={BOTTOM}
                  x2={W}
                  y2={BOTTOM}
                  stroke-width="0.8"
                  style="stroke: var(--scope-grid);"
                />
                {#each snapshot.models as m (m.name)}
                  <path
                    d={smoothArea(m.ema)}
                    fill="url(#sl-area-{v.key}-{m.name})"
                    stroke="none"
                  />
                  <path
                    d={smoothLine(m.ema)}
                    fill="none"
                    stroke-width="1.6"
                    filter="url(#sl-glow-{v.key})"
                    style="stroke: {m.color};"
                  />
                {/each}
              {:else if v.key === 'ribbon'}
                <line
                  x1="0"
                  y1={H / 2}
                  x2={W}
                  y2={H / 2}
                  stroke-width="0.4"
                  stroke-dasharray="2 4"
                  style="stroke: var(--scope-grid);"
                />
                {#each snapshot.models as m (m.name)}
                  <path
                    d={ribbonBand(m.ema)}
                    fill="url(#sl-area-{v.key}-{m.name})"
                    stroke-width="1"
                    filter="url(#sl-glow-{v.key})"
                    style="stroke: {m.color};"
                  />
                {/each}
              {:else if v.key === 'particles'}
                <line
                  x1="0"
                  y1={BOTTOM}
                  x2={W}
                  y2={BOTTOM}
                  stroke-width="0.8"
                  style="stroke: var(--scope-grid);"
                />
                {#each snapshot.models as m (m.name)}
                  {#each particles(m.ema) as p, i (i)}
                    <circle
                      cx={p.x.toFixed(1)}
                      cy={p.y.toFixed(1)}
                      r={p.r.toFixed(1)}
                      opacity={p.opacity.toFixed(2)}
                      filter="url(#sl-glow-{v.key})"
                      style="fill: {m.color};"
                    />
                  {/each}
                {/each}
              {:else if v.key === 'halo'}
                {#each snapshot.models as m, i (m.name)}
                  {@const total = Math.max(1, snapshot.models.length)}
                  {@const cx = ((i + 0.5) / total) * W}
                  {@const cy = H / 2}
                  {@const intensity = m.live}
                  {@const baseR = 18}
                  {@const r = baseR + intensity * 48}
                  <circle
                    {cx}
                    {cy}
                    r={(r + 30).toFixed(1)}
                    fill="url(#sl-halo-{v.key}-{m.name})"
                    opacity={(0.4 + intensity * 0.6).toFixed(2)}
                  />
                  <circle
                    {cx}
                    {cy}
                    r={r.toFixed(1)}
                    fill="none"
                    stroke-width="1.5"
                    filter="url(#sl-glow-{v.key})"
                    style="stroke: {m.color};"
                    opacity={(0.7 + intensity * 0.3).toFixed(2)}
                  />
                {/each}
              {/if}
            </svg>
          </div>
          <div class="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[10px] font-mono">
            {#each snapshot.models as m (m.name)}
              <span class="flex items-center gap-1.5" style="color: {m.color};">
                <span
                  class="w-2 h-2 rounded-full inline-block"
                  style="background: {m.color};"
                ></span>
                {m.name}
                <span class="opacity-70">· {m.tps.toFixed(1)} tok/s</span>
              </span>
            {/each}
          </div>
        </Section>
      </Card>
    {/each}
  </div>
</div>
