<script>
  import { onMount, onDestroy } from 'svelte';
  import { getLoaded, getGpu, fmtBytes, fmtParams } from '../api.js';

  let loaded = $state([]);
  let gpu = $state(null);
  let pollHandle;

  async function refresh() {
    try {
      [loaded, gpu] = await Promise.all([getLoaded(), getGpu()]);
    } catch (_) {
      /* ignore */
    }
  }

  onMount(() => {
    refresh();
    pollHandle = setInterval(refresh, 1500);
  });

  onDestroy(() => clearInterval(pollHandle));
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-5xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-heading mb-1">System</h1>
      <p class="text-sm text-muted">
        Live view of GPU and Ollama runtime state. Updates every 1.5s.
      </p>
    </div>

    <!-- GPU -->
    <section class="bg-surface border border-border rounded-lg p-5">
      <h2 class="text-xs uppercase tracking-wider text-muted mb-3 font-mono">gpu</h2>
      {#if !gpu || !gpu.available}
        <div class="text-muted text-sm">No GPU detected (or nvidia-smi unavailable).</div>
      {:else}
        {#each gpu.gpus as g (g.name)}
          <div class="space-y-3">
            <div class="text-heading font-mono">{g.name}</div>
            <div class="grid grid-cols-3 gap-4">
              <div>
                <div class="text-xs text-muted font-mono uppercase mb-1">vram</div>
                <div class="text-lg font-mono text-body">
                  {(g.memory_used_mb / 1024).toFixed(1)}
                  <span class="text-muted text-sm">
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
                <div class="text-xs text-muted font-mono uppercase mb-1">utilization</div>
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
    </section>

    <!-- Loaded models -->
    <section class="bg-surface border border-border rounded-lg p-5">
      <h2 class="text-xs uppercase tracking-wider text-muted mb-3 font-mono">loaded in vram</h2>
      {#if loaded.length === 0}
        <div class="text-muted text-sm">
          No models currently loaded. Send a message to warm one up.
        </div>
      {:else}
        <div class="space-y-2">
          {#each loaded as m (m.name)}
            <div class="bg-surface-2 border border-border rounded p-3">
              <div class="flex items-baseline justify-between gap-3 flex-wrap">
                <div class="font-mono text-heading">{m.name}</div>
                <div class="text-xs text-muted font-mono">
                  {fmtParams(m.details?.parameter_size)} · {m.details?.quantization_level}
                </div>
              </div>
              <div class="grid grid-cols-3 gap-3 text-xs font-mono mt-2">
                <div>
                  <div class="text-muted text-[10px] uppercase">vram</div>
                  <div class="text-body">{fmtBytes(m.size_vram)}</div>
                </div>
                <div>
                  <div class="text-muted text-[10px] uppercase">disk</div>
                  <div class="text-body">{fmtBytes(m.size)}</div>
                </div>
                <div>
                  <div class="text-muted text-[10px] uppercase">context</div>
                  <div class="text-body">{m.context_length || '—'}</div>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </section>
  </div>
</div>
