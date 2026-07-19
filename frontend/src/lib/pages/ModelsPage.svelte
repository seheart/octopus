<script>
  import { onMount, onDestroy } from 'svelte';
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
  import { Card, Button } from '../components/ui/index.js';
  import { modelHints } from '../modelHints.js';
  import Oscilloscope from '../components/Oscilloscope.svelte';

  let models = $state([]);
  let loaded = $state([]);
  let loading = $state(true);
  let err = $state(null);
  // Kept separate from `err`: a failed delete/unload must not replace the
  // (still perfectly loaded) model list with the load-error card.
  let actionErr = $state(null);
  let unloadingName = $state('');

  /** @type {ReturnType<typeof setInterval> | undefined} */
  let pollHandle;

  async function refresh() {
    const [m, l] = await Promise.allSettled([getModels(), getLoaded()]);
    if (m.status === 'fulfilled') {
      models = m.value;
      err = null;
    } else {
      err = m.reason?.message || 'failed to load models';
    }
    if (l.status === 'fulfilled') loaded = l.value;
    loading = false;
  }

  onMount(() => {
    refresh();
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

  async function unload(name, e) {
    e?.stopPropagation();
    if (unloadingName) return;
    unloadingName = name;
    actionErr = null;
    try {
      await unloadModel(name);
      await refresh();
    } catch (e2) {
      actionErr = e2.message;
    } finally {
      unloadingName = '';
    }
  }

  async function confirmDelete(name, size, e) {
    e?.stopPropagation();
    // Native confirm shows the size being freed so the user knows what they
    // get back. Cancel is a one-click out (no "click trash twice" puzzle).
    const ok = confirm(
      `Delete ${name}?\n\nThis frees ${fmtBytes(size)} on disk. The model can be re-installed later from the catalog.`
    );
    if (!ok) return;
    actionErr = null;
    try {
      await deleteModel(name);
      if (selectedModel.value === name) setModel('');
      await refresh();
    } catch (e2) {
      actionErr = e2.message;
    }
  }
</script>

<div class="h-full flex flex-col lg:flex-row gap-6 px-6 py-6 overflow-hidden">
  <!-- LEFT: live oscilloscope.  Collapses to a thin strip when nothing is
       happening — a black rectangle saying "no models loaded" is visual
       weight that teaches a novice nothing. -->
  <div
    class="lg:w-2/5 flex flex-col {loaded.length === 0 ? 'min-h-0' : 'min-h-[280px] lg:min-h-0'}"
  >
    <div class="mb-2 shrink-0">
      <div class="text-xs font-mono text-muted uppercase tracking-wider">
        Live activity · {loaded.length}
        {loaded.length === 1 ? 'model' : 'models'} in memory
      </div>
      <div class="text-[10px] font-mono text-muted opacity-70 mt-0.5">
        Every spike is one chat request, from any Ollama client on this machine.
      </div>
    </div>
    {#if loaded.length === 0}
      <div
        class="rounded border border-dashed border-border bg-surface px-3 py-3 text-xs text-muted"
      >
        Live token activity will appear here once a model is warm in memory.
      </div>
    {:else}
      <div class="flex-1 min-h-0">
        <Oscilloscope models={loaded} />
      </div>
    {/if}
  </div>

  <!-- RIGHT: header + installed models, scrollable -->
  <div class="flex-1 overflow-y-auto min-h-0 space-y-6">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-heading mb-1">Models</h1>
        <p class="text-sm text-muted">
          Everything installed on this machine. Click a card to chat with it.
        </p>
      </div>
      <Button variant="secondary" size="md" onclick={() => go('pull')}>+ Add a model</Button>
    </div>

    <div>
      <div class="text-xs font-mono text-muted uppercase tracking-wider mb-2">
        Installed · {models.length}
      </div>

      {#if actionErr}
        <div class="text-error text-xs font-mono mb-2" role="alert">
          That didn't work: {actionErr}
        </div>
      {/if}

      {#if loading}
        <div class="text-muted text-sm font-mono">Loading…</div>
      {:else if err}
        <Card>
          <div class="text-center text-sm py-6 space-y-3">
            <div class="text-error">Couldn't load your models.</div>
            <div class="flex justify-center gap-2">
              <Button variant="secondary" onclick={refresh}>Try again</Button>
              <Button variant="ghost" onclick={() => go('diagnostic')}>Diagnose →</Button>
            </div>
          </div>
        </Card>
      {:else if models.length === 0}
        <Card>
          <div class="text-center text-sm py-6 space-y-2">
            <div class="text-muted">No models installed yet.</div>
            <Button variant="primary" onclick={() => go('pull')}>Install your first →</Button>
          </div>
        </Card>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-3">
          {#each models as m (m.name)}
            {@const hints = modelHints(m)}
            {@const loadedNow = isLoaded(m.name)}
            <!-- Whole-card click → pickModel. Inner buttons stopPropagation. -->
            <div
              role="button"
              tabindex={hints.chatCapable ? 0 : -1}
              onclick={() => hints.chatCapable && pickModel(m.name)}
              onkeydown={(e) => {
                if (hints.chatCapable && (e.key === 'Enter' || e.key === ' ')) {
                  e.preventDefault();
                  pickModel(m.name);
                }
              }}
              aria-label="Use {m.name} in chat"
              aria-disabled={!hints.chatCapable}
              class="border rounded-lg p-4 transition-colors group flex flex-col text-left {hints.chatCapable
                ? 'cursor-pointer'
                : 'cursor-default'} {loadedNow
                ? 'bg-success/15 border-success/60 hover:border-success'
                : 'bg-surface border-border hover:border-accent'}"
            >
              <div class="flex items-start justify-between mb-2 gap-2">
                <div class="text-heading font-mono text-sm font-medium truncate flex-1 min-w-0">
                  {m.name}
                </div>
                <div class="flex items-center gap-1.5 shrink-0">
                  {#if loadedNow}
                    <!-- Status badge: non-interactive, just a state read-out -->
                    <span
                      class="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-success/20 text-success font-mono"
                      title="This model is warmed into memory and ready to respond"
                    >
                      <span class="w-1.5 h-1.5 rounded-full bg-success" aria-hidden="true"></span>
                      In memory
                    </span>
                    <!-- Separate action: evict from memory -->
                    <button
                      onclick={(e) => unload(m.name, e)}
                      disabled={unloadingName === m.name}
                      title="Evict {m.name} from memory (stays installed on disk)"
                      aria-label="Evict {m.name} from memory"
                      class="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded text-muted hover:text-error hover:bg-error/10 transition-colors font-mono disabled:opacity-60"
                    >
                      {unloadingName === m.name ? 'Evicting…' : 'Evict'}
                    </button>
                  {/if}
                  <button
                    onclick={(e) => confirmDelete(m.name, m.size, e)}
                    class="opacity-0 group-hover:opacity-100 focus:opacity-100 text-muted hover:text-error transition-opacity p-1"
                    aria-label="Delete {m.name}"
                    title="Delete {m.name} ({fmtBytes(m.size)})"
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
                </div>
              </div>
              <!-- "Best for" — the teaching line -->
              <p class="text-sm text-body leading-snug mb-3">
                <span class="text-muted text-xs font-mono uppercase tracking-wider mr-1"
                  >Best for</span
                >
                {hints.bestFor}
              </p>

              <div class="grid grid-cols-3 gap-2 text-xs font-mono">
                <div title="Number of parameters — bigger usually means smarter and slower">
                  <div class="text-muted text-[10px] uppercase">Size class</div>
                  <div class="text-body">{fmtParams(m.details?.parameter_size) || '—'}</div>
                </div>
                <div title="How much disk this model takes">
                  <div class="text-muted text-[10px] uppercase">On disk</div>
                  <div class="text-body">{fmtBytes(m.size)}</div>
                </div>
                <div title="Compression level — smaller = faster, less accurate">
                  <div class="text-muted text-[10px] uppercase">Compression</div>
                  <div class="text-body">{m.details?.quantization_level || '—'}</div>
                </div>
              </div>

              <div class="flex items-center justify-between gap-3 mt-3 pt-3 border-t border-border">
                <div class="text-xs text-muted font-mono truncate">
                  {m.details?.family || '—'} · {ollamaTimeAgo(m.modified_at)}
                </div>
                {#if hints.tryPrompt}
                  <button
                    onclick={(e) => {
                      e.stopPropagation();
                      tryPrompt(m.name, hints.tryPrompt);
                    }}
                    class="text-xs font-medium text-accent hover:underline shrink-0"
                    title={`Open chat with this prompt seeded:\n"${hints.tryPrompt}"`}
                    aria-label="Try a starter prompt with {m.name}"
                  >
                    Try a prompt →
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
