<script>
  import { onMount } from 'svelte';
  import {
    getModels,
    getLoaded,
    deleteModel,
    unloadModel,
    fmtBytes,
    fmtParams,
    ollamaTimeAgo
  } from '../api.js';
  import { go } from '../stores/route.svelte.js';
  import { setModel, selectedModel, setPendingPrompt } from '../stores/model.svelte.js';
  import { Card } from '../components/ui/index.js';
  import { modelHints } from '../modelHints.js';

  let models = $state([]);
  let loaded = $state([]);
  let loading = $state(true);
  let err = $state(null);

  // Delete confirmation per-model name
  let confirmingDelete = $state('');

  // Tracks which model is currently being unloaded (so we can show "stopping…")
  let unloadingName = $state('');

  async function refresh() {
    try {
      [models, loaded] = await Promise.all([getModels(), getLoaded()]);
      err = null;
    } catch (e) {
      err = e.message;
    }
    loading = false;
  }

  onMount(refresh);

  function isLoaded(name) {
    return loaded.some((m) => m.name === name);
  }

  function pickModel(name) {
    setModel(name);
    go('chat');
  }

  function tryPrompt(name, prompt) {
    setModel(name);
    setPendingPrompt(prompt);
    go('chat');
  }

  async function unload(name) {
    if (unloadingName) return;
    unloadingName = name;
    try {
      await unloadModel(name);
      await refresh();
    } catch (e) {
      err = e.message;
    } finally {
      unloadingName = '';
    }
  }

  async function confirmDelete(name) {
    if (confirmingDelete !== name) {
      confirmingDelete = name;
      // Auto-clear confirm if user doesn't act in 5s
      setTimeout(() => {
        if (confirmingDelete === name) confirmingDelete = '';
      }, 5000);
      return;
    }
    try {
      await deleteModel(name);
      // If we deleted the currently-selected model, clear selection.
      if (selectedModel.value === name) setModel('');
      confirmingDelete = '';
      await refresh();
    } catch (e) {
      err = e.message;
      confirmingDelete = '';
    }
  }
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-5xl mx-auto space-y-6">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-heading mb-1">Models</h1>
        <p class="text-sm text-muted">
          All Ollama models on this machine. Click a card to chat with it.
        </p>
      </div>
      <button
        onclick={() => go('pull')}
        class="text-sm font-mono px-3 py-1.5 bg-surface-2 border border-border rounded hover:border-accent hover:text-accent transition-colors text-body shrink-0"
      >
        + Add a model
      </button>
    </div>

    <!-- Installed -->
    <div>
      <div class="text-xs font-mono text-muted uppercase tracking-wider mb-2">
        installed · {models.length}
      </div>

      {#if loading}
        <div class="text-muted text-sm font-mono">loading…</div>
      {:else if err}
        <div class="text-error text-sm font-mono">error: {err}</div>
      {:else if models.length === 0}
        <Card>
          <div class="text-center text-sm py-6 space-y-2">
            <div class="text-muted">No models installed yet.</div>
            <button
              onclick={() => go('pull')}
              class="text-accent hover:underline font-mono text-sm"
            >
              Add a model →
            </button>
          </div>
        </Card>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          {#each models as m (m.name)}
            {@const hints = modelHints(m)}
            {@const loadedNow = isLoaded(m.name)}
            <div
              class="border rounded-lg p-4 transition-colors group flex flex-col {loadedNow
                ? 'bg-success/15 border-success/60 hover:border-success'
                : 'bg-surface border-border hover:border-accent'}"
            >
              <div class="flex items-start justify-between mb-2 gap-2">
                <button
                  onclick={() => hints.chatCapable && pickModel(m.name)}
                  disabled={!hints.chatCapable}
                  class="text-left flex-1 min-w-0 disabled:cursor-default"
                  aria-label="Use {m.name} in chat"
                >
                  <div class="text-heading font-mono text-sm font-medium truncate">{m.name}</div>
                </button>
                <div class="flex items-center gap-1.5 shrink-0">
                  {#if isLoaded(m.name)}
                    <button
                      onclick={() => unload(m.name)}
                      disabled={unloadingName === m.name}
                      title="Unload {m.name} from memory (model stays installed)"
                      aria-label="Unload {m.name} from memory"
                      class="group/loaded text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-surface-2 text-success font-mono hover:bg-error hover:text-canvas transition-colors disabled:opacity-60"
                    >
                      {#if unloadingName === m.name}
                        stopping…
                      {:else}
                        <span class="group-hover/loaded:hidden">loaded</span>
                        <span class="hidden group-hover/loaded:inline">stop</span>
                      {/if}
                    </button>
                  {/if}
                  {#if confirmingDelete === m.name}
                    <button
                      onclick={() => confirmDelete(m.name)}
                      class="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-error text-canvas font-mono hover:opacity-90"
                      aria-label="Confirm delete {m.name}"
                    >
                      confirm
                    </button>
                  {:else}
                    <button
                      onclick={() => confirmDelete(m.name)}
                      class="opacity-0 group-hover:opacity-100 text-muted hover:text-error transition-opacity p-1"
                      aria-label="Delete {m.name}"
                      title="Delete {m.name}"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        aria-hidden="true"
                      >
                        <path d="M3 6h18" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
                        <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  {/if}
                </div>
              </div>
              <!-- "Best for" — the teaching line, not a label -->
              <p class="text-sm text-body leading-snug mb-3">
                <span class="text-muted text-xs font-mono uppercase tracking-wider mr-1"
                  >best for</span
                >
                {hints.bestFor}
              </p>

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

              <div class="flex items-center justify-between gap-3 mt-3 pt-3 border-t border-border">
                <div class="text-xs text-muted font-mono">
                  {m.details?.family || '—'} · modified {ollamaTimeAgo(m.modified_at)}
                </div>
                {#if hints.tryPrompt}
                  <button
                    onclick={() => tryPrompt(m.name, hints.tryPrompt)}
                    class="text-xs text-accent hover:underline font-mono shrink-0"
                    title={hints.tryPrompt}
                    aria-label="Try this prompt with {m.name}"
                  >
                    try this prompt →
                  </button>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>
