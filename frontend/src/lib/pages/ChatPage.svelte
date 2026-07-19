<script>
  import { onMount, onDestroy } from 'svelte';
  import { getModels, getLoaded, getGpu, chatStream, fmtBytes, fmtParams } from '../api.js';
  import { selectedModel, setModel, consumePendingPrompt } from '../stores/model.svelte.js';
  import { recordToken } from '../stores/activity.svelte.js';
  import { renderMarkdown } from '../markdown.js';
  import { codeCopy } from '../markdownActions.js';
  import { modelHints } from '../modelHints.js';
  import { go } from '../stores/route.svelte.js';
  import { Button } from '../components/ui/index.js';

  let models = $state([]);
  let messages = $state([]);
  let input = $state('');
  let streaming = $state(false);
  let liveStat = $state(null);
  let loaded = $state([]);
  let gpu = $state(null);
  let warmupActive = $state(false);
  let copyJustCopied = $state(-1);
  let modelsLoadError = $state(null);
  // True only after the first /api/models call returns, so we don't flash
  // the "no models yet" panel before we know.
  let modelsLoaded = $state(false);
  /** @type {ReturnType<typeof setInterval> | undefined} */
  let pollHandle;
  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let warmupHandle;
  /** @type {HTMLElement | undefined} */
  let scrollEl = $state();
  /** @type {HTMLTextAreaElement | undefined} */
  let inputEl = $state();
  /** @type {ReturnType<typeof chatStream> | null} */
  let currentChat = null;
  // Stay pinned to bottom UNLESS the user has scrolled up to re-read; flips
  // back on once they return to within 50px of the bottom.
  let pinnedToBottom = true;

  function replaceLast(msg) {
    messages = [...messages.slice(0, -1), msg];
  }

  // For the empty-chat state, derive 3 starter prompts from the currently
  // selected model's modelHints. Falls back to the general default if no
  // model is selected.
  const currentHints = $derived.by(() => {
    const m = models.find((mm) => mm.name === selectedModel.value);
    return m ? modelHints(m) : null;
  });

  // Generic warmup prompts shown only when there's no selected model.
  const fallbackPrompts = [
    'Explain async/await in JavaScript with a simple example.',
    'Write a Python function that returns the n-th Fibonacci number, memoized.',
    'Summarize the difference between SQLite WAL and rollback journal modes.'
  ];

  onMount(async () => {
    await loadModels();
    await refresh();
    pollHandle = setInterval(refresh, 2000);
    const seed = consumePendingPrompt();
    if (seed) input = seed;
    inputEl?.focus();
    window.addEventListener('octopus:new-chat', onNewChat);
  });

  onDestroy(() => {
    clearInterval(pollHandle);
    clearTimeout(warmupHandle);
    currentChat?.abort();
    window.removeEventListener('octopus:new-chat', onNewChat);
  });

  function onNewChat() {
    if (streaming) stop();
    messages = [];
    liveStat = null;
    input = '';
    inputEl?.focus();
  }

  async function loadModels() {
    try {
      const all = await getModels();
      models = all.filter((m) => !m.name.includes('embed'));
      // Persist selection across reloads; pick first available if nothing valid.
      if (!selectedModel.value || !models.some((m) => m.name === selectedModel.value)) {
        if (models.length) setModel(models[0].name);
      }
      modelsLoadError = null;
    } catch (e) {
      modelsLoadError = e?.message || 'Could not reach the backend.';
    } finally {
      modelsLoaded = true;
    }
  }

  async function refresh() {
    const [l, g] = await Promise.allSettled([getLoaded(), getGpu()]);
    if (l.status === 'fulfilled') loaded = l.value;
    if (g.status === 'fulfilled') gpu = g.value;
  }

  async function send(prompt = input) {
    if (!prompt.trim() || streaming || !selectedModel.value) return;
    const userMsg = { role: 'user', content: prompt.trim() };
    const asstMsg = { role: 'assistant', content: '', model: selectedModel.value, stats: {} };
    messages = [...messages, userMsg, asstMsg];
    input = '';
    streaming = true;
    liveStat = null;
    warmupActive = false;
    pinnedToBottom = true;
    scrollToBottom();

    warmupHandle = setTimeout(() => {
      if (streaming && !messages[messages.length - 1].content) warmupActive = true;
    }, 2500);

    const conv = messages
      .filter((m) => m.role !== 'assistant' || m.content)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      currentChat = chatStream({ model: selectedModel.value, messages: conv }, (evt) => {
        const last = messages[messages.length - 1];
        if (evt.type === 'token') {
          last.content += evt.content;
          replaceLast(last);
          warmupActive = false;
          recordToken(selectedModel.value);
          scrollToBottom();
        } else if (evt.type === 'thinking') {
          last.thinking = (last.thinking || '') + evt.content;
          replaceLast(last);
          warmupActive = false;
          scrollToBottom();
        } else if (evt.type === 'ttft') {
          liveStat = { ...(liveStat || {}), ttft_ms: evt.ms };
        } else if (evt.type === 'done') {
          last.stats = {
            ttft_ms: liveStat?.ttft_ms,
            tokens_per_sec: evt.tokens_per_sec,
            eval_count: evt.eval_count,
            total_ms: evt.total_ms
          };
          replaceLast(last);
          liveStat = last.stats;
        } else if (evt.type === 'error') {
          last.content = (last.content || '') + `\n\n_Error: ${evt.message}_`;
          replaceLast(last);
          warmupActive = false;
        }
      });
      await currentChat.done;
    } catch (err) {
      if (err.name !== 'AbortError') {
        const last = messages[messages.length - 1];
        last.content = (last.content || '') + `\n\n_Error: ${err.message}_`;
        replaceLast(last);
      }
    } finally {
      streaming = false;
      warmupActive = false;
      currentChat = null;
      clearTimeout(warmupHandle);
      refresh();
    }
  }

  function stop() {
    currentChat?.abort();
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function scrollToBottom() {
    if (!pinnedToBottom) return;
    queueMicrotask(() => {
      if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
    });
  }

  function onScroll() {
    if (!scrollEl) return;
    // Treat "within 50px of bottom" as pinned, to tolerate slight rounding.
    pinnedToBottom = scrollEl.scrollTop + scrollEl.clientHeight >= scrollEl.scrollHeight - 50;
  }

  function clearChat() {
    if (messages.length > 4 && !confirm('Clear this conversation?')) return;
    messages = [];
    liveStat = null;
  }

  async function copyMessage(content, idx) {
    try {
      await navigator.clipboard.writeText(content);
      copyJustCopied = idx;
      setTimeout(() => {
        if (copyJustCopied === idx) copyJustCopied = -1;
      }, 1500);
    } catch (_e) {
      /* ignore */
    }
  }

  function useExample(text) {
    input = text;
    inputEl?.focus();
  }

  // Three starter-friendly model recommendations for the "no models" empty
  // state. Sizes are approximate (educational, not load-bearing).
  const starterModels = [
    {
      name: 'llama3.2:3b',
      size: '~2 GB',
      desc: 'Small and fast. A friendly first pick.'
    },
    {
      name: 'llama3.1:8b',
      size: '~4.7 GB',
      desc: 'Better answers, still quick on most GPUs.'
    },
    {
      name: 'qwen3:8b',
      size: '~5 GB',
      desc: 'Thinks before it answers. Stronger on hard questions.'
    }
  ];

  const placeholder = $derived(
    selectedModel.value ? `Message ${selectedModel.value}` : 'Pick a model above to start'
  );

  const canSend = $derived(!!selectedModel.value && !!input.trim() && !streaming);
</script>

<div class="h-full flex overflow-hidden">
  <main class="flex-1 flex flex-col overflow-hidden">
    <!-- Model picker + clear. Picker is hidden when there are no models at
         all (the empty state below takes over). -->
    {#if models.length > 0}
      <div
        class="px-4 py-2 border-b border-border bg-surface flex items-center justify-between gap-3"
      >
        <label class="flex items-center gap-2 min-w-0 text-xs text-muted">
          <span class="shrink-0">Model</span>
          <select
            value={selectedModel.value}
            onchange={(e) => setModel(e.currentTarget.value)}
            class="bg-surface-2 text-body border border-border rounded px-2 py-1 text-sm font-mono focus:outline-none focus:border-accent max-w-md"
            aria-label="Select chat model"
          >
            {#each models as m (m.name)}
              <option value={m.name}>{m.name} · {fmtParams(m.details?.parameter_size)}</option>
            {/each}
          </select>
        </label>
        <Button
          variant="secondary"
          size="sm"
          onclick={clearChat}
          disabled={messages.length === 0 || streaming}
        >
          Clear
        </Button>
      </div>
    {/if}

    <div
      bind:this={scrollEl}
      onscroll={onScroll}
      class="flex-1 overflow-y-auto px-6 py-4 space-y-4"
    >
      {#if !modelsLoaded}
        <!-- Loading skeleton to avoid the empty-flash. -->
        <div class="h-full flex items-center justify-center text-sm text-muted">Loading…</div>
      {:else if modelsLoadError}
        <div class="h-full flex items-center justify-center">
          <div class="max-w-md w-full space-y-3 text-center">
            <h2 class="text-lg font-semibold text-heading">Can't reach the backend.</h2>
            <p class="text-sm text-muted">{modelsLoadError}</p>
            <Button variant="primary" onclick={() => go('diagnostic')}>Open Diagnostic →</Button>
          </div>
        </div>
      {:else if models.length === 0}
        <!-- First-run welcome: zero chat models on disk. -->
        <div class="h-full flex items-center justify-center">
          <div class="max-w-xl w-full space-y-5">
            <div class="text-center space-y-1.5">
              <h2 class="text-2xl font-bold text-heading">Welcome to Octopus.</h2>
              <p class="text-sm text-muted">
                You'll chat with AI models running on your own computer — nothing leaves this
                machine.
              </p>
            </div>
            <div class="space-y-2">
              <div class="text-xs text-muted uppercase tracking-wider font-mono">
                Get your first model
              </div>
              {#each starterModels as s, i (s.name)}
                <button
                  onclick={() => {
                    setModel(s.name);
                    go('pull');
                  }}
                  class="block w-full text-left bg-surface border border-border rounded p-3 hover:border-accent transition-colors"
                >
                  <div class="flex items-baseline justify-between gap-3 mb-1">
                    <div class="font-mono text-sm font-medium text-heading">{s.name}</div>
                    <div class="text-xs text-muted font-mono">{s.size}</div>
                  </div>
                  <div class="text-sm text-body">{s.desc}</div>
                  <div class="text-xs text-accent mt-1 font-mono">
                    Install {i === 0 ? '(recommended for starters)' : ''} →
                  </div>
                </button>
              {/each}
            </div>
            <div class="text-center text-xs text-muted">
              <button
                onclick={() => go('pull')}
                class="bg-transparent border-0 p-0 text-accent hover:underline cursor-pointer font-mono text-xs"
              >
                Browse all options →
              </button>
            </div>
          </div>
        </div>
      {:else if messages.length === 0}
        <!-- Chat empty state — model is selected; pull a starter prompt
             from modelHints so the user has a one-click way to start. -->
        <div class="h-full flex items-center justify-center">
          <div class="max-w-lg w-full space-y-5">
            <div class="text-center space-y-1.5">
              <h2 class="text-xl font-semibold text-heading">
                Chatting with <span class="font-mono">{selectedModel.value}</span>
              </h2>
              {#if currentHints?.bestFor}
                <p class="text-sm text-muted">Best for {currentHints.bestFor}.</p>
              {/if}
            </div>
            {#if currentHints?.tryPrompt}
              <Button
                variant="primary"
                size="lg"
                onclick={() => {
                  input = currentHints.tryPrompt;
                  send();
                }}
              >
                Try: {currentHints.tryPrompt.length > 60
                  ? currentHints.tryPrompt.slice(0, 60) + '…'
                  : currentHints.tryPrompt}
              </Button>
            {/if}
            <div class="space-y-2">
              <div class="text-xs text-muted font-mono uppercase tracking-wider">
                or try one of these
              </div>
              {#each fallbackPrompts as p (p)}
                <button
                  onclick={() => useExample(p)}
                  class="block w-full text-left text-sm bg-surface border border-border rounded p-2.5 hover:border-accent hover:bg-surface-2 transition-colors text-body"
                >
                  {p}
                </button>
              {/each}
            </div>
          </div>
        </div>
      {/if}

      {#each messages as msg, i (i)}
        <div class="flex flex-col gap-1 group">
          <div class="flex items-center justify-between">
            <div class="text-xs text-muted font-mono uppercase tracking-wide">
              {msg.role === 'user' ? 'you' : msg.model || 'assistant'}
            </div>
            {#if msg.role === 'assistant' && msg.content}
              <button
                onclick={() => copyMessage(msg.content, i)}
                class="opacity-0 group-hover:opacity-100 text-xs text-muted hover:text-accent font-mono transition-opacity"
                aria-label="Copy message"
              >
                {copyJustCopied === i ? '✓ copied' : 'copy'}
              </button>
            {/if}
          </div>
          {#if msg.role === 'assistant'}
            {#if msg.thinking}
              <details class="text-xs text-muted mb-1">
                <summary class="cursor-pointer font-mono hover:text-body select-none">
                  thinking{!msg.content ? '…' : ''}
                </summary>
                <div
                  class="mt-1.5 pl-3 border-l-2 border-border italic font-sans whitespace-pre-wrap leading-relaxed"
                >
                  {msg.thinking}
                </div>
              </details>
            {/if}
            <div class="markdown-body text-body" use:codeCopy>
              {#if msg.content}
                <!-- eslint-disable-next-line svelte/no-at-html-tags — DOMPurify-sanitized in markdown.js -->
                {@html renderMarkdown(msg.content)}
              {:else if streaming && i === messages.length - 1 && msg.thinking}
                <span class="text-muted italic">Drafting answer…</span>
              {:else if streaming && i === messages.length - 1 && warmupActive}
                <span class="text-muted italic"
                  >Loading {msg.model} into memory (first request can take ~10s)…</span
                >
              {/if}{#if streaming && i === messages.length - 1}<span
                  class="inline-block w-2 h-4 bg-accent animate-pulse ml-0.5 align-middle"
                ></span>{/if}
            </div>
          {:else}
            <div class="whitespace-pre-wrap text-heading">{msg.content}</div>
          {/if}
          {#if msg.role === 'assistant' && msg.stats?.tokens_per_sec}
            <!-- Per-message metrics with hover tooltips that translate the
                 jargon. Keeps mono units as data; uses sentence-case labels. -->
            <div class="text-xs text-muted font-mono pt-1 flex flex-wrap gap-x-2 gap-y-0.5">
              <span title="How fast the model is producing text (tokens ≈ ¾ of a word)">
                Speed <span class="text-body">{msg.stats.tokens_per_sec} tok/s</span>
              </span>
              <span aria-hidden="true" class="opacity-50">·</span>
              <span title="Time until the model produced the first token of its reply">
                First reply <span class="text-body">{msg.stats.ttft_ms}ms</span>
              </span>
              <span aria-hidden="true" class="opacity-50">·</span>
              <span title="Total tokens generated in this reply">
                Length <span class="text-body">{msg.stats.eval_count} tok</span>
              </span>
              <span aria-hidden="true" class="opacity-50">·</span>
              <span title="Total wall-clock time for this reply">
                Total <span class="text-body">{(msg.stats.total_ms / 1000).toFixed(1)}s</span>
              </span>
            </div>
          {/if}
        </div>
      {/each}
    </div>

    {#if models.length > 0}
      <div class="border-t border-border bg-surface px-4 py-3">
        <div class="flex gap-2 items-end">
          <textarea
            bind:this={inputEl}
            bind:value={input}
            onkeydown={onKey}
            {placeholder}
            rows="2"
            class="flex-1 bg-surface-2 border border-border rounded px-3 py-2 text-sm resize-none focus:outline-none focus:border-accent text-body disabled:opacity-60"
            disabled={streaming || !selectedModel.value}
            aria-label="Message"></textarea>
          {#if streaming}
            <Button variant="danger" size="lg" onclick={stop} ariaLabel="Stop generation">
              Stop
            </Button>
          {:else}
            <Button
              variant="primary"
              size="lg"
              onclick={() => send()}
              disabled={!canSend}
              ariaLabel={canSend ? 'Send message' : 'Pick a model and type a message to send'}
            >
              Send
            </Button>
          {/if}
        </div>
        {#if !selectedModel.value}
          <div class="text-xs text-muted mt-1.5">
            Pick a model in the dropdown above to start chatting.
          </div>
        {:else}
          <div class="text-[11px] text-muted mt-1.5 font-mono opacity-70">
            Enter to send · Shift+Enter for a new line · ⌘K to jump anywhere
          </div>
        {/if}
      </div>
    {/if}
  </main>

  <!-- Telemetry sidebar -->
  <aside
    class="w-80 border-l border-border bg-surface overflow-y-auto p-4 text-sm space-y-5 hidden lg:block"
  >
    <section>
      <h2 class="text-xs uppercase tracking-wider text-muted mb-2 font-mono">Last response</h2>
      {#if liveStat}
        <div class="space-y-1 font-mono">
          <div
            class="flex justify-between"
            title="How fast the model produced text (tokens ≈ ¾ of a word)"
          >
            <span class="text-muted">Speed</span>
            <span class="text-accent">{liveStat.tokens_per_sec ?? '–'} tok/s</span>
          </div>
          <div class="flex justify-between" title="Time until the first token of the reply">
            <span class="text-muted">First reply</span>
            <span>{liveStat.ttft_ms ?? '–'}ms</span>
          </div>
          <div class="flex justify-between" title="Total tokens in this reply">
            <span class="text-muted">Length</span>
            <span>{liveStat.eval_count ?? '–'} tok</span>
          </div>
          <div class="flex justify-between" title="Total wall-clock time for this reply">
            <span class="text-muted">Total time</span>
            <span>{liveStat.total_ms ? (liveStat.total_ms / 1000).toFixed(1) + 's' : '–'}</span>
          </div>
        </div>
      {:else}
        <div class="text-muted text-xs">No response yet.</div>
      {/if}
    </section>

    <section>
      <h2
        class="text-xs uppercase tracking-wider text-muted mb-2 font-mono"
        title="Models currently warmed into RAM/VRAM"
      >
        In memory
      </h2>
      {#if loaded.length === 0}
        <div class="text-muted text-xs">Nothing loaded right now.</div>
      {:else}
        <div class="space-y-2 font-mono">
          {#each loaded as m (m.name)}
            <div class="bg-surface-2 rounded p-2 border border-border">
              <div class="text-body text-xs truncate">{m.name}</div>
              <div class="flex justify-between text-xs text-muted mt-1">
                <span>{fmtBytes(m.size_vram)}</span>
                <span>{fmtParams(m.details?.parameter_size)}</span>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </section>

    <section>
      <h2 class="text-xs uppercase tracking-wider text-muted mb-2 font-mono">GPU</h2>
      {#if !gpu || !gpu.available}
        <div class="text-muted text-xs">Not available.</div>
      {:else}
        {#each gpu.gpus as g (g.name)}
          <div class="space-y-1.5 font-mono">
            <div class="text-body text-xs truncate">{g.name}</div>
            <div>
              <div class="flex justify-between text-xs mb-0.5">
                <span class="text-muted" title="GPU memory in use">vram</span>
                <span
                  >{(g.memory_used_mb / 1024).toFixed(1)} / {(g.memory_total_mb / 1024).toFixed(0)} GB</span
                >
              </div>
              <div class="h-1.5 bg-surface-2 rounded overflow-hidden">
                <div
                  class="h-full bg-accent"
                  style="width: {((g.memory_used_mb / g.memory_total_mb) * 100).toFixed(1)}%"
                ></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-xs mb-0.5">
                <span class="text-muted" title="GPU utilization right now">util</span>
                <span>{g.utilization_pct}%</span>
              </div>
              <div class="h-1.5 bg-surface-2 rounded overflow-hidden">
                <div class="h-full bg-accent" style="width: {g.utilization_pct}%"></div>
              </div>
            </div>
            <div class="flex justify-between text-xs">
              <span class="text-muted">temp</span>
              <span>{g.temp_c}°C</span>
            </div>
          </div>
        {/each}
      {/if}
    </section>
  </aside>
</div>
