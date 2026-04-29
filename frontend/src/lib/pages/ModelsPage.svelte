<script>
  import { onMount } from 'svelte';
  import { getModels, getLoaded, fmtBytes, fmtParams, ollamaTimeAgo } from '../api.js';
  import { go } from '../stores/route.svelte.js';

  let models = $state([]);
  let loaded = $state([]);
  let loading = $state(true);
  let err = $state(null);

  onMount(async () => {
    try {
      [models, loaded] = await Promise.all([getModels(), getLoaded()]);
    } catch (e) {
      err = e.message;
    }
    loading = false;
  });

  function isLoaded(name) {
    return loaded.some(m => m.name === name);
  }
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-5xl mx-auto">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-heading mb-1">Models</h1>
      <p class="text-sm text-muted">All Ollama models on this machine. Click one to chat with it.</p>
    </div>

    {#if loading}
      <div class="text-muted text-sm font-mono">loading…</div>
    {:else if err}
      <div class="text-error text-sm font-mono">error: {err}</div>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        {#each models as m}
          <button
            onclick={() => { /* TODO: set chat model */ go('chat'); }}
            class="text-left bg-surface border border-border rounded-lg p-4 hover:border-accent transition-colors"
          >
            <div class="flex items-start justify-between mb-2 gap-2">
              <div class="flex-1 min-w-0">
                <div class="text-heading font-mono text-sm font-medium truncate">{m.name}</div>
                <div class="text-xs text-muted font-mono">{m.details?.family || '—'}</div>
              </div>
              {#if isLoaded(m.name)}
                <span class="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-surface-2 text-success font-mono">loaded</span>
              {/if}
            </div>
            <div class="grid grid-cols-3 gap-2 text-xs font-mono">
              <div>
                <div class="text-muted text-[10px] uppercase">params</div>
                <div class="text-body">{fmtParams(m.details?.parameter_size) || '—'}</div>
              </div>
              <div>
                <div class="text-muted text-[10px] uppercase">size</div>
                <div class="text-body">{fmtBytes(m.size)}</div>
              </div>
              <div>
                <div class="text-muted text-[10px] uppercase">quant</div>
                <div class="text-body">{m.details?.quantization_level || '—'}</div>
              </div>
            </div>
            <div class="text-xs text-muted font-mono mt-2">
              modified {ollamaTimeAgo(m.modified_at)}
            </div>
          </button>
        {/each}
      </div>
    {/if}
  </div>
</div>
