<script>
  import { onMount } from 'svelte';
  import {
    getModels,
    getLoaded,
    deleteModel,
    pullModel,
    fmtBytes,
    fmtParams,
    ollamaTimeAgo
  } from '../api.js';
  import { go } from '../stores/route.svelte.js';
  import { setModel, selectedModel, setPendingPrompt } from '../stores/model.svelte.js';
  import { Button, Card, Section } from '../components/ui/index.js';
  import { modelHints } from '../modelHints.js';

  let models = $state([]);
  let loaded = $state([]);
  let loading = $state(true);
  let err = $state(null);

  // Pull state
  let pullName = $state('');
  let pulling = $state(false);
  let pullStatus = $state('');
  let pullPct = $state(null);
  let pullError = $state(null);
  let currentPull = $state(null);

  // Delete confirmation per-model name
  let confirmingDelete = $state('');

  const suggestions = [
    { name: 'llama3.2:3b', desc: 'small, fast general' },
    { name: 'phi4', desc: 'modern 14B from MS' },
    { name: 'mistral:7b', desc: 'classic, reliable' },
    { name: 'deepseek-r1:14b', desc: 'reasoning' },
    { name: 'qwen3:8b', desc: 'smaller qwen3' },
    { name: 'nomic-embed-text', desc: 'embeddings (RAG)' }
  ];

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

  async function startPull(name = pullName) {
    const target = name.trim();
    if (!target || pulling) return;
    pulling = true;
    pullStatus = 'starting…';
    pullPct = null;
    pullError = null;
    pullName = target;

    try {
      currentPull = pullModel(target, (evt) => {
        if (evt.status === 'error') {
          pullError = evt.error || 'pull failed';
          return;
        }
        pullStatus = evt.status;
        if (evt.total && evt.completed !== null && evt.completed !== undefined) {
          pullPct = Math.min(100, (evt.completed / evt.total) * 100);
        }
      });
      await currentPull.done;
      if (!pullError) {
        pullStatus = 'done';
        pullName = '';
        await refresh();
        // If no model is currently selected, pick the one we just pulled
        if (!selectedModel.value) setModel(target);
      }
    } catch (e) {
      if (e.name !== 'AbortError') pullError = e.message;
    } finally {
      pulling = false;
      currentPull = null;
      // Clear status after a beat so it doesn't linger
      setTimeout(() => {
        if (!pulling) {
          pullStatus = '';
          pullPct = null;
        }
      }, 2000);
    }
  }

  function cancelPull() {
    currentPull?.abort();
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

  function onPullKey(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      startPull();
    }
  }
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-5xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-heading mb-1">Models</h1>
      <p class="text-sm text-muted">
        All Ollama models on this machine. Click a card to chat with it. Pull new ones below.
      </p>
    </div>

    <!-- Pull section -->
    <Card padding="lg">
      <Section title="add a model">
        <div class="flex gap-2 items-center mb-3">
          <input
            type="text"
            bind:value={pullName}
            onkeydown={onPullKey}
            placeholder="model name (e.g. qwen3:8b, llama3.2:3b)"
            disabled={pulling}
            class="flex-1 bg-surface-2 border border-border rounded px-3 py-1.5 text-sm font-mono focus:outline-none focus:border-accent text-body disabled:opacity-50"
          />
          {#if pulling}
            <Button variant="secondary" onclick={cancelPull}>cancel</Button>
          {:else}
            <Button variant="primary" onclick={() => startPull()} disabled={!pullName.trim()}>
              pull
            </Button>
          {/if}
        </div>

        {#if pulling || pullError || pullStatus === 'done'}
          <div class="bg-surface-2 border border-border rounded p-3 mb-3 font-mono text-xs">
            <div class="flex justify-between mb-1">
              <span class="text-body">{pullName || '—'}</span>
              <span class="text-muted">
                {#if pullError}
                  <span class="text-error">{pullError}</span>
                {:else}
                  {pullStatus}
                  {#if pullPct !== null}
                    · {pullPct.toFixed(1)}%
                  {/if}
                {/if}
              </span>
            </div>
            {#if pullPct !== null && !pullError}
              <div class="h-1.5 bg-canvas rounded overflow-hidden">
                <div class="h-full bg-accent transition-all" style="width: {pullPct}%"></div>
              </div>
            {/if}
          </div>
        {/if}

        <div class="text-xs text-muted font-mono uppercase tracking-wider mb-2">
          popular suggestions
        </div>
        <div class="flex flex-wrap gap-1.5">
          {#each suggestions as s (s.name)}
            <button
              onclick={() => startPull(s.name)}
              disabled={pulling ||
                models.some((m) => m.name === s.name || m.name.startsWith(s.name + ':'))}
              title={s.desc}
              class="text-xs font-mono px-2 py-1 bg-surface-2 border border-border rounded hover:border-accent hover:text-accent transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-body"
            >
              {s.name}
              <span class="text-muted">· {s.desc}</span>
            </button>
          {/each}
        </div>
      </Section>
    </Card>

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
          <div class="text-center text-muted text-sm py-4">
            No models installed yet. Try one of the suggestions above to get started.
          </div>
        </Card>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          {#each models as m (m.name)}
            {@const hints = modelHints(m)}
            <div
              class="bg-surface border border-border rounded-lg p-4 hover:border-accent transition-colors group flex flex-col"
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
                    <span
                      class="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-surface-2 text-success font-mono"
                    >
                      loaded
                    </span>
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
