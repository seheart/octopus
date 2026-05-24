<script>
  import { onMount, onDestroy } from 'svelte';
  import { getModels, getHostInfo, deleteModel, fmtBytes, fmtParams } from '../api.js';
  import { go } from '../stores/route.svelte.js';
  import { setModel, selectedModel } from '../stores/model.svelte.js';
  import { Card, Section, StatRow } from '../components/ui/index.js';

  let models = $state([]);
  let host = $state(null);
  let err = $state(null);
  let loading = $state(true);
  /** @type {ReturnType<typeof setInterval> | undefined} */
  let pollHandle;

  async function refresh() {
    const [m, h] = await Promise.allSettled([getModels(), getHostInfo()]);
    if (m.status === 'fulfilled') {
      models = m.value;
      err = null;
    } else {
      err = m.reason?.message || 'failed to load models';
    }
    if (h.status === 'fulfilled') host = h.value;
    loading = false;
  }

  onMount(() => {
    refresh();
    pollHandle = setInterval(refresh, 5000);
  });

  onDestroy(() => clearInterval(pollHandle));

  // Sort biggest first so the heaviest models show up at the top.
  const sorted = $derived([...models].sort((a, b) => (b.size || 0) - (a.size || 0)));
  const totalOllamaBytes = $derived(models.reduce((s, m) => s + (m.size || 0), 0));
  const biggest = $derived(sorted[0]?.size || 0);

  function pct(part, total) {
    if (!total) return 0;
    return (part / total) * 100;
  }

  async function confirmDeleteModel(name, size) {
    const ok = confirm(
      `Delete ${name}?\n\nThis frees ${fmtBytes(size)} on disk. The model can be re-installed later from the catalog.`
    );
    if (!ok) return;
    try {
      await deleteModel(name);
      if (selectedModel.value === name) setModel('');
      await refresh();
    } catch (e) {
      err = e.message;
    }
  }
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-5xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-heading mb-1">Storage</h1>
      <p class="text-sm text-muted">
        What Ollama models are taking up on disk. Sorted biggest first — useful when you're trying
        to free up space.
      </p>
    </div>

    <!-- Top: Ollama footprint vs free disk -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card padding="lg">
        <Section title="ollama footprint">
          <div class="space-y-1.5">
            <StatRow label="models installed" value={models.length} accent />
            <StatRow label="total on disk" value={fmtBytes(totalOllamaBytes)} />
            <StatRow
              label="biggest model"
              value={sorted[0] ? `${sorted[0].name} · ${fmtBytes(sorted[0].size)}` : '—'}
            />
          </div>
        </Section>
      </Card>

      <Card padding="lg">
        <Section title="root filesystem">
          {#if !host?.disk}
            <div class="text-muted text-sm">loading…</div>
          {:else}
            <div class="space-y-2">
              <div class="flex justify-between text-xs font-mono">
                <span class="text-muted uppercase">used</span>
                <span class="text-body">
                  {fmtBytes(host.disk.used_bytes)} / {fmtBytes(host.disk.total_bytes)}
                  <span class="text-muted">
                    · {pct(host.disk.used_bytes, host.disk.total_bytes).toFixed(1)}%
                  </span>
                </span>
              </div>
              <div class="h-2 bg-surface-2 rounded overflow-hidden">
                <div
                  class="h-full bg-accent transition-all"
                  style="width: {pct(host.disk.used_bytes, host.disk.total_bytes)}%"
                ></div>
              </div>
              <div class="text-xs font-mono text-muted">
                {fmtBytes(host.disk.free_bytes)} free
              </div>
            </div>
          {/if}
        </Section>
      </Card>
    </div>

    <!-- Per-model breakdown -->
    <div>
      <div class="flex items-baseline justify-between mb-2">
        <div class="text-xs font-mono text-muted uppercase tracking-wider">
          by model · {models.length}
        </div>
        <button
          onclick={() => go('models')}
          class="text-xs font-mono text-muted hover:text-accent transition-colors"
        >
          manage in Models →
        </button>
      </div>

      {#if loading}
        <div class="text-muted text-sm font-mono">Loading…</div>
      {:else if err}
        <Card>
          <div class="text-center text-sm py-6 space-y-3">
            <div class="text-error">Couldn't load storage info.</div>
            <button
              onclick={refresh}
              class="bg-transparent border border-border text-body hover:border-accent rounded px-3 py-1.5 text-sm font-mono cursor-pointer"
            >
              Try again
            </button>
          </div>
        </Card>
      {:else if models.length === 0}
        <Card>
          <div class="text-center text-muted text-sm py-6">
            No models installed — nothing taking up space.
          </div>
        </Card>
      {:else}
        <Card padding="lg">
          <div class="space-y-3">
            {#each sorted as m (m.name)}
              <div class="group">
                <div class="flex items-baseline justify-between gap-3 mb-1">
                  <div class="flex items-baseline gap-2 min-w-0">
                    <div class="font-mono text-sm text-heading truncate">{m.name}</div>
                    <div class="text-[10px] font-mono text-muted shrink-0">
                      {fmtParams(m.details?.parameter_size) || '—'} · {m.details
                        ?.quantization_level || '—'}
                    </div>
                  </div>
                  <div class="flex items-center gap-3 shrink-0">
                    <span class="text-xs font-mono text-body">{fmtBytes(m.size)}</span>
                    <span class="text-[10px] font-mono text-muted w-12 text-right">
                      {pct(m.size, totalOllamaBytes).toFixed(1)}%
                    </span>
                    <button
                      onclick={() => confirmDeleteModel(m.name, m.size)}
                      class="opacity-0 group-hover:opacity-100 focus:opacity-100 text-muted hover:text-error transition-opacity text-[10px] font-mono uppercase tracking-wider px-1"
                      aria-label="Delete {m.name}"
                      title="Delete {m.name} ({fmtBytes(m.size)})"
                    >
                      Delete
                    </button>
                  </div>
                </div>
                <div class="h-1.5 bg-surface-2 rounded overflow-hidden">
                  <div
                    class="h-full bg-accent transition-all"
                    style="width: {pct(m.size, biggest)}%"
                  ></div>
                </div>
              </div>
            {/each}
          </div>
        </Card>
      {/if}
    </div>
  </div>
</div>
