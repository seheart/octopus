<script>
  import { onMount, onDestroy } from 'svelte';
  import {
    getModels,
    getLoaded,
    getOllamaInfo,
    deleteModel,
    unloadModel,
    fmtBytes,
    fmtParams,
    ollamaTimeAgo
  } from '../api.js';
  import { go } from '../stores/route.svelte.js';
  import { setModel, selectedModel, setPendingPrompt } from '../stores/model.svelte.js';
  import { modelHints } from '../modelHints.js';
  import Oscilloscope from '../components/Oscilloscope.svelte';
  import GetStarted from '../components/GetStarted.svelte';

  let models = $state([]);
  let loaded = $state([]);
  let loading = $state(true);
  let err = $state(null);
  // Whether `ollama serve` is up — drives the Get Started card vs. the grid.
  let ollamaReachable = $state(true);

  // Delete confirmation per-model name
  let confirmingDelete = $state('');

  // Tracks which model is currently being unloaded (so we can show "stopping…")
  let unloadingName = $state('');

  /** @type {ReturnType<typeof setInterval> | undefined} */
  let pollHandle;

  async function refresh() {
    const [m, l, o] = await Promise.allSettled([getModels(), getLoaded(), getOllamaInfo()]);
    if (m.status === 'fulfilled') {
      models = m.value;
      err = null;
    } else {
      err = m.reason?.message || 'failed to load models';
    }
    if (l.status === 'fulfilled') loaded = l.value;
    if (o.status === 'fulfilled') ollamaReachable = o.value.reachable;
    loading = false;
  }

  onMount(() => {
    refresh();
    // Re-poll so the scope sees newly-loaded / unloaded models.
    pollHandle = setInterval(refresh, 2000);
  });
  onDestroy(() => clearInterval(pollHandle));

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

<div class="h-full flex flex-col lg:flex-row gap-6 px-6 py-6 overflow-hidden">
  <!-- LEFT: live oscilloscope, big, always visible -->
  <div class="lg:w-2/5 flex flex-col min-h-[280px] lg:min-h-0">
    <div class="mb-2 shrink-0">
      <div
        class="text-xs font-mono text-muted uppercase tracking-wider cursor-help"
        title="A model is 'in VRAM' once it's loaded into GPU memory — Ollama keeps it warm for a few minutes after use, then frees it."
      >
        live activity · {loaded.length}
        {loaded.length === 1 ? 'model' : 'models'} in vram
      </div>
      <div class="text-[10px] font-mono text-muted opacity-70 mt-0.5">
        all Ollama clients · spikes per request
      </div>
    </div>
    <div class="flex-1 min-h-0">
      <Oscilloscope models={loaded} />
    </div>
  </div>

  <!-- RIGHT: header + installed models, scrollable -->
  <div class="flex-1 overflow-y-auto min-h-0 space-y-6">
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
      {:else if !ollamaReachable || models.length === 0}
        <GetStarted {ollamaReachable} hasModels={models.length > 0} />
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-3">
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
                  <div
                    class="text-muted text-[10px] uppercase cursor-help"
                    title="Parameters, in billions — the model's size. More can mean smarter, but slower and heavier."
                  >
                    params
                  </div>
                  <div class="text-body">{fmtParams(m.details?.parameter_size) || '—'}</div>
                </div>
                <div>
                  <div
                    class="text-muted text-[10px] uppercase cursor-help"
                    title="Disk space the model file takes up."
                  >
                    size
                  </div>
                  <div class="text-body">{fmtBytes(m.size)}</div>
                </div>
                <div>
                  <div
                    class="text-muted text-[10px] uppercase cursor-help"
                    title="Quantization — how compressed the weights are. Q4 = 4-bit: smaller and faster, with a slight quality tradeoff."
                  >
                    quant
                  </div>
                  <div class="text-body">{m.details?.quantization_level || '—'}</div>
                </div>
              </div>

              <div class="flex items-center justify-between gap-3 mt-3 pt-3 border-t border-border">
                <div class="text-xs text-muted font-mono">
                  <span
                    class="cursor-help"
                    title="The model family this is built on (llama, gemma, qwen…). Same family, similar behaviour."
                    >{m.details?.family || '—'}</span
                  >
                  · modified {ollamaTimeAgo(m.modified_at)}
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
