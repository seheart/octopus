<script>
  import { onMount, onDestroy } from 'svelte';
  import {
    getModels,
    getLoaded,
    getGpu,
    getOllamaInfo,
    getHostInfo,
    fmtBytes,
    fmtParams,
    fmtUptime
  } from '../api.js';
  import { Card, Section, Tag, StatRow } from '../components/ui/index.js';

  let loaded = $state([]);
  let allModels = $state([]);
  let gpu = $state(null);
  let ollama = $state(null);
  let host = $state(null);
  /** @type {ReturnType<typeof setInterval> | undefined} */
  let pollHandle;

  async function refresh() {
    // Use allSettled so one 404 doesn't black out every panel.
    const [l, g, o, h, m] = await Promise.allSettled([
      getLoaded(),
      getGpu(),
      getOllamaInfo(),
      getHostInfo(),
      getModels()
    ]);
    if (l.status === 'fulfilled') loaded = l.value;
    if (g.status === 'fulfilled') gpu = g.value;
    if (o.status === 'fulfilled') ollama = o.value;
    if (h.status === 'fulfilled') host = h.value;
    if (m.status === 'fulfilled') allModels = m.value;
  }

  onMount(() => {
    refresh();
    pollHandle = setInterval(refresh, 2000);
  });

  onDestroy(() => clearInterval(pollHandle));

  // Derived: total disk used by Ollama models
  const totalModelBytes = $derived(allModels.reduce((sum, m) => sum + (m.size || 0), 0));
  const loadedVramBytes = $derived(loaded.reduce((sum, m) => sum + (m.size_vram || 0), 0));

  // Total parameters (rough — sum of parameter_size strings parsed)
  function parseParamsB(s) {
    if (!s) return 0;
    const match = String(s).match(/([\d.]+)\s*B/i);
    return match ? parseFloat(match[1]) : 0;
  }
  const totalParamsB = $derived(
    allModels.reduce((sum, m) => sum + parseParamsB(m.details?.parameter_size), 0)
  );

  function pct(used, total) {
    if (!total) return 0;
    return ((used / total) * 100).toFixed(1);
  }
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-5xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-baseline justify-between">
      <div>
        <h1 class="text-2xl font-bold text-heading mb-1">System</h1>
        <p class="text-sm text-muted">
          Live view of host hardware, Ollama runtime, GPU, and model inventory. Refreshes every 2s.
        </p>
      </div>
      <div class="text-xs font-mono text-muted">
        {ollama?.reachable ? 'live' : 'no connection'}
      </div>
    </div>

    <!-- Top row: connection + inventory summary -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Ollama connection -->
      <Card padding="lg">
        <Section title="ollama">
          {#if !ollama}
            <div class="text-muted text-sm">checking…</div>
          {:else}
            <div class="space-y-1.5">
              <StatRow
                label="status"
                value={ollama.reachable ? 'connected' : 'unreachable'}
                accent={ollama.reachable}
              />
              <StatRow label="version" value={ollama.version || '–'} />
              <StatRow label="url" value={ollama.url} />
            </div>
          {/if}
        </Section>
      </Card>

      <!-- Inventory summary -->
      <Card padding="lg">
        <Section title="inventory">
          <div class="space-y-1.5">
            <StatRow label="models installed" value={allModels.length} accent />
            <StatRow
              label="total parameters"
              value="{totalParamsB.toFixed(1)}B"
              hint="Parameters across all your models, in billions — a model's 'size'. More can mean smarter, but heavier to run."
            />
            <StatRow label="total disk used" value={fmtBytes(totalModelBytes)} />
            <StatRow
              label="loaded in vram"
              value="{loaded.length} ({fmtBytes(loadedVramBytes)})"
              hint="Models currently held in GPU memory, warmed up and ready to respond instantly."
            />
          </div>
        </Section>
      </Card>
    </div>

    <!-- Host (CPU + memory + disk + uptime) -->
    <Card padding="lg">
      <Section title="host">
        {#if !host}
          <div class="text-muted text-sm">loading…</div>
        {:else}
          <div class="space-y-4">
            <!-- CPU + uptime row. Each field renders only when known, so a
                 platform that can't report one shows a clean card, not "—". -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div class="text-xs text-muted font-mono uppercase mb-1">cpu</div>
                {#if host.cpu?.model && host.cpu.model !== 'unknown'}
                  <div class="text-sm text-heading font-mono truncate">{host.cpu.model}</div>
                  <div class="text-xs text-muted font-mono mt-0.5">
                    {host.cpu?.cores || 0} cores
                  </div>
                {:else}
                  <div class="text-sm text-heading font-mono">{host.cpu?.cores || 0} cores</div>
                {/if}
              </div>
              {#if host.uptime_seconds !== null && host.uptime_seconds !== undefined}
                <div>
                  <div class="text-xs text-muted font-mono uppercase mb-1">uptime</div>
                  <div class="text-sm text-heading font-mono">
                    {fmtUptime(host.uptime_seconds)}
                  </div>
                </div>
              {/if}
            </div>

            <!-- Memory bar — live usage on Linux; total-only where /proc
                 isn't available and we fall back to sysconf. -->
            {#if host.memory}
              <div>
                <div class="flex justify-between text-xs font-mono mb-0.5">
                  <span class="text-muted uppercase">memory</span>
                  {#if host.memory.used_bytes !== null}
                    <span class="text-body">
                      {fmtBytes(host.memory.used_bytes)} / {fmtBytes(host.memory.total_bytes)}
                      <span class="text-muted">
                        · {pct(host.memory.used_bytes, host.memory.total_bytes)}%
                      </span>
                    </span>
                  {:else}
                    <span class="text-body">{fmtBytes(host.memory.total_bytes)} total</span>
                  {/if}
                </div>
                {#if host.memory.used_bytes !== null}
                  <div class="h-2 bg-surface-2 rounded overflow-hidden">
                    <div
                      class="h-full bg-accent transition-all"
                      style="width: {pct(host.memory.used_bytes, host.memory.total_bytes)}%"
                    ></div>
                  </div>
                {/if}
              </div>
            {/if}

            <!-- Disk bar -->
            {#if host.disk}
              <div>
                <div class="flex justify-between text-xs font-mono mb-0.5">
                  <span class="text-muted uppercase">disk (root)</span>
                  <span class="text-body">
                    {fmtBytes(host.disk.used_bytes)} / {fmtBytes(host.disk.total_bytes)}
                    <span class="text-muted">
                      · {pct(host.disk.used_bytes, host.disk.total_bytes)}% · {fmtBytes(
                        host.disk.free_bytes
                      )} free
                    </span>
                  </span>
                </div>
                <div class="h-2 bg-surface-2 rounded overflow-hidden">
                  <div
                    class="h-full bg-accent transition-all"
                    style="width: {pct(host.disk.used_bytes, host.disk.total_bytes)}%"
                  ></div>
                </div>
              </div>
            {/if}
          </div>
        {/if}
      </Section>
    </Card>

    <!-- GPU -->
    <Card padding="lg">
      <Section title="gpu">
        {#if !gpu || !gpu.available}
          <div class="text-muted text-sm">No GPU detected (or nvidia-smi unavailable).</div>
        {:else}
          {#each gpu.gpus as g (g.name)}
            <div class="space-y-3">
              <div class="text-heading font-mono">{g.name}</div>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <div
                    class="text-xs text-muted font-mono uppercase mb-1 cursor-help"
                    title="Video memory on the GPU. A model has to fit here (or in system RAM) to run."
                  >
                    vram
                  </div>
                  <div class="text-lg font-mono text-body">
                    {(g.memory_used_mb / 1024).toFixed(1)}<span class="text-muted text-sm">
                      / {(g.memory_total_mb / 1024).toFixed(0)} GB</span
                    >
                  </div>
                  <div class="h-2 bg-surface-2 rounded overflow-hidden mt-1">
                    <div
                      class="h-full bg-accent transition-all"
                      style="width: {((g.memory_used_mb / g.memory_total_mb) * 100).toFixed(1)}%"
                    ></div>
                  </div>
                </div>
                <div>
                  <div
                    class="text-xs text-muted font-mono uppercase mb-1 cursor-help"
                    title="How hard the GPU is working right now — it climbs toward 100% while a model generates."
                  >
                    utilization
                  </div>
                  <div class="text-lg font-mono text-body">
                    {g.utilization_pct}<span class="text-muted text-sm">%</span>
                  </div>
                  <div class="h-2 bg-surface-2 rounded overflow-hidden mt-1">
                    <div
                      class="h-full bg-accent transition-all"
                      style="width: {g.utilization_pct}%"
                    ></div>
                  </div>
                </div>
                <div>
                  <div class="text-xs text-muted font-mono uppercase mb-1">temperature</div>
                  <div class="text-lg font-mono text-body">
                    {g.temp_c}<span class="text-muted text-sm">°C</span>
                  </div>
                </div>
              </div>
            </div>
          {/each}
        {/if}
      </Section>
    </Card>

    <!-- Loaded models -->
    <Card padding="lg">
      <Section title="loaded in vram">
        {#if loaded.length === 0}
          <div class="text-muted text-sm">
            No models currently loaded. Send a message in chat to warm one up.
          </div>
        {:else}
          <div class="space-y-2">
            {#each loaded as m (m.name)}
              <div class="bg-surface-2 border border-border rounded p-3">
                <div class="flex items-baseline justify-between gap-3 flex-wrap">
                  <div class="font-mono text-heading">{m.name}</div>
                  <div class="flex items-center gap-2">
                    <Tag tone="success">live</Tag>
                    <span class="text-xs text-muted font-mono">
                      {fmtParams(m.details?.parameter_size)} · {m.details?.quantization_level}
                    </span>
                  </div>
                </div>
                <div class="grid grid-cols-3 gap-3 text-xs font-mono mt-2">
                  <div>
                    <div
                      class="text-muted text-[10px] uppercase cursor-help"
                      title="GPU memory this model is using while loaded."
                    >
                      vram
                    </div>
                    <div class="text-body">{fmtBytes(m.size_vram)}</div>
                  </div>
                  <div>
                    <div class="text-muted text-[10px] uppercase">disk</div>
                    <div class="text-body">{fmtBytes(m.size)}</div>
                  </div>
                  <div>
                    <div
                      class="text-muted text-[10px] uppercase cursor-help"
                      title="Context length — how much text (in tokens) the model can consider at once."
                    >
                      context
                    </div>
                    <div class="text-body">{m.context_length || '—'}</div>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </Section>
    </Card>
  </div>
</div>
