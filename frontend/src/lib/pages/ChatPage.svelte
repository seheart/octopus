<script>
  import { onMount, onDestroy } from 'svelte';
  import {
    getModels,
    getLoaded,
    getGpu,
    getOllamaInfo,
    getHostInfo,
    fmtBytes,
    fmtParams
  } from '../api.js';
  import { selectedModel, setModel, consumePendingPrompt } from '../stores/model.svelte.js';
  import { go } from '../stores/route.svelte.js';
  import { recordToken } from '../stores/activity.svelte.js';
  import { renderMarkdown } from '../markdown.js';
  import { modelFit } from '../modelFit.js';
  import { Button } from '../components/ui/index.js';
  import GetStarted from '../components/GetStarted.svelte';

  // Every installed chat model (embeddings excluded). `models` derives from
  // this — the subset that will actually run on this machine.
  let allModels = $state([]);
  let host = $state(null);
  // Whether `ollama serve` is up — drives the Get Started card on first run.
  let ollamaReachable = $state(true);
  let messages = $state([]);
  let input = $state('');
  let streaming = $state(false);
  let liveStat = $state(null);
  let loaded = $state([]);
  let gpu = $state(null);
  let warmupActive = $state(false);
  let copyJustCopied = $state(-1);

  // --- Hardware-aware model gating -----------------------------------------
  // gemma3:12b (~8 GB) loaded on an 8 GB machine froze it solid. The picker
  // only offers models that fit; the rest are hidden, and send() refuses
  // them as a backstop against a stale stored selection.
  const ramBytes = $derived(host?.memory?.total_bytes || 0);
  const vramBytes = $derived(
    gpu?.available ? gpu.gpus.reduce((sum, g) => sum + (g.memory_total_mb || 0) * 1e6, 0) : 0
  );
  const fitOf = (m) => modelFit(m.size, { ramBytes, vramBytes });
  const models = $derived(allModels.filter((m) => fitOf(m).tier !== 'wont-fit'));
  const hiddenModels = $derived(allModels.filter((m) => fitOf(m).tier === 'wont-fit'));

  // Keep the selection valid: if the chosen model isn't an offered (installed
  // and runnable) one, fall back to the first that is.
  $effect(() => {
    if (models.length && !models.some((m) => m.name === selectedModel.value)) {
      setModel(models[0].name);
    }
  });

  /** @type {AbortController | null} */
  let currentAbort = null;
  /** @type {ReturnType<typeof setInterval> | undefined} */
  let pollHandle;
  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let warmupHandle;
  let scrollEl;
  /** @type {HTMLTextAreaElement | undefined} */
  let inputEl;

  const examplePrompts = [
    'Explain async/await in JavaScript with a simple example.',
    'Write a Python function that returns the n-th Fibonacci number, memoized.',
    'What are three good system prompts for code review?',
    'Summarize the difference between SQLite WAL and rollback journal modes.'
  ];

  onMount(async () => {
    await loadModels();
    await refresh();
    pollHandle = setInterval(refresh, 2000);
    // If we got here from a "Try this prompt" click, seed the input.
    const seed = consumePendingPrompt();
    if (seed) input = seed;
    inputEl?.focus();
  });

  onDestroy(() => {
    clearInterval(pollHandle);
    clearTimeout(warmupHandle);
    currentAbort?.abort();
  });

  async function loadModels() {
    try {
      const all = await getModels();
      allModels = all.filter((m) => !m.name.includes('embed'));
      // Selection validity (stored model still offered?) is handled by the
      // $effect above, so it reacts to the runnable list changing too.
    } catch (_e) {
      /* backend offline — the Banner explains it */
    }
  }

  async function refresh() {
    const [l, g, o, h] = await Promise.allSettled([
      getLoaded(),
      getGpu(),
      getOllamaInfo(),
      getHostInfo()
    ]);
    if (l.status === 'fulfilled') loaded = l.value;
    if (g.status === 'fulfilled') gpu = g.value;
    if (o.status === 'fulfilled') ollamaReachable = o.value.reachable;
    if (h.status === 'fulfilled') host = h.value;
    // While the user has no models at all, keep re-detecting so the Get
    // Started card checks itself off the moment a pull finishes.
    if (allModels.length === 0) loadModels();
  }

  async function send(prompt = input) {
    if (!prompt.trim() || streaming || !selectedModel.value) return;
    // Backstop against the gemma3:12b freeze: never start a chat with a
    // model too big for this machine. The picker already hides these, so
    // this only catches a stale stored selection before the effect fixes it.
    const picked = allModels.find((m) => m.name === selectedModel.value);
    if (picked && fitOf(picked).tier === 'wont-fit') return;
    const userMsg = { role: 'user', content: prompt.trim() };
    const asstMsg = { role: 'assistant', content: '', model: selectedModel.value, stats: {} };
    messages = [...messages, userMsg, asstMsg];
    input = '';
    streaming = true;
    liveStat = null;
    warmupActive = false;
    scrollToBottom();

    // Show "warming up" hint if no token after 2.5s.
    warmupHandle = setTimeout(() => {
      if (streaming && !messages[messages.length - 1].content) warmupActive = true;
    }, 2500);

    const conv = messages
      .filter((m) => m.role !== 'assistant' || m.content)
      .map((m) => ({ role: m.role, content: m.content }));

    currentAbort = new AbortController();

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ model: selectedModel.value, messages: conv }),
        signal: currentAbort.signal
      });

      if (!resp.ok) throw new Error(`chat failed: ${resp.status}`);
      if (!resp.body) throw new Error('chat failed: empty response body');
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n\n');
        buf = lines.pop();
        for (const block of lines) {
          const line = block.split('\n').find((l) => l.startsWith('data: '));
          if (!line) continue;
          const evt = JSON.parse(line.slice(6));
          const last = messages[messages.length - 1];
          if (evt.type === 'token') {
            last.content += evt.content;
            messages = [...messages.slice(0, -1), last];
            warmupActive = false;
            // Real per-model signal for the Oscilloscope on the Models page.
            recordToken(selectedModel.value);
            scrollToBottom();
          } else if (evt.type === 'thinking') {
            last.thinking = (last.thinking || '') + evt.content;
            messages = [...messages.slice(0, -1), last];
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
            messages = [...messages.slice(0, -1), last];
            liveStat = last.stats;
          } else if (evt.type === 'error') {
            // Backend surfaces structured errors when Ollama drops mid-stream.
            last.content = (last.content || '') + `\n\n_Error: ${evt.message}_`;
            messages = [...messages.slice(0, -1), last];
            warmupActive = false;
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        const last = messages[messages.length - 1];
        last.content = (last.content || '') + `\n\n_Error: ${err.message}_`;
        messages = [...messages.slice(0, -1), last];
      }
    } finally {
      streaming = false;
      warmupActive = false;
      currentAbort = null;
      clearTimeout(warmupHandle);
      refresh();
    }
  }

  function stop() {
    currentAbort?.abort();
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function scrollToBottom() {
    queueMicrotask(() => {
      if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
    });
  }

  function clearChat() {
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
</script>

<div class="h-full flex overflow-hidden">
  <!-- Chat panel -->
  <main class="flex-1 flex flex-col overflow-hidden">
    <div
      class="px-4 py-2 border-b border-border bg-surface flex items-center justify-between gap-3"
    >
      <div class="flex items-center gap-2 min-w-0">
        <select
          value={selectedModel.value}
          onchange={(e) => setModel(e.currentTarget.value)}
          title="Pick which model answers. The number is its size in billions of parameters — bigger is often smarter but slower."
          class="bg-surface-2 text-body border border-border rounded px-2 py-1 text-sm font-mono focus:outline-none focus:border-accent max-w-md"
        >
          {#each models as m (m.name)}
            <option value={m.name}>{m.name} · {fmtParams(m.details?.parameter_size)}</option>
          {/each}
        </select>
        {#if hiddenModels.length > 0}
          <span
            class="text-xs font-mono text-muted shrink-0"
            title="Too large for this machine ({fmtBytes(ramBytes)} RAM): {hiddenModels
              .map((m) => m.name)
              .join(', ')}"
          >
            {hiddenModels.length} hidden · won't fit
          </span>
        {/if}
      </div>
      <Button
        variant="secondary"
        size="sm"
        onclick={clearChat}
        disabled={messages.length === 0 || streaming}
      >
        clear
      </Button>
    </div>

    <div bind:this={scrollEl} class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      {#if messages.length === 0}
        <div class="h-full flex items-center justify-center">
          <div class="max-w-md w-full space-y-6">
            {#if allModels.length === 0}
              <!-- Nothing installed yet — guide first-run setup. -->
              <GetStarted {ollamaReachable} hasModels={false} />
            {:else if models.length === 0}
              <!-- Models are installed, but every one is too big to run
                   here — pulling a smaller one is the way forward. -->
              <div class="bg-surface border border-border rounded-lg p-5 text-center space-y-3">
                <div class="text-heading font-medium text-sm">
                  Your models are too large for this machine
                </div>
                <p class="text-sm text-muted">
                  All {allModels.length} installed model{allModels.length === 1 ? '' : 's'} need more
                  memory than this machine has ({fmtBytes(ramBytes)} RAM). A smaller model will get you
                  chatting.
                </p>
                <button
                  onclick={() => go('pull')}
                  class="text-accent hover:underline font-mono text-sm"
                >
                  Browse smaller models →
                </button>
              </div>
            {:else}
              <div class="text-center space-y-2">
                <h2 class="text-xl font-bold text-heading">pick a model · ask anything</h2>
                <p class="text-sm text-muted">
                  Stream tokens with live timing. Stats appear in the sidebar.
                </p>
              </div>
              <div class="space-y-2">
                <div class="text-xs text-muted font-mono uppercase tracking-wider">
                  try one of these
                </div>
                {#each examplePrompts as p (p)}
                  <button
                    onclick={() => useExample(p)}
                    class="block w-full text-left text-sm bg-surface border border-border rounded p-2.5 hover:border-accent hover:bg-surface-2 transition-colors text-body"
                  >
                    {p}
                  </button>
                {/each}
              </div>
            {/if}
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
              <details class="text-xs text-muted mb-1 group/think">
                <summary
                  class="cursor-pointer font-mono uppercase tracking-wider hover:text-body select-none"
                  title="Some models reason step by step before answering — this is that thinking. Click to expand."
                >
                  <span class="opacity-60">▸</span> thinking
                  {#if !msg.content}
                    <span class="ml-1 italic">(reasoning…)</span>
                  {/if}
                </summary>
                <div
                  class="mt-1.5 pl-3 border-l-2 border-border italic font-sans whitespace-pre-wrap leading-relaxed"
                >
                  {msg.thinking}
                </div>
              </details>
            {/if}
            <div class="markdown-body text-body">
              {#if msg.content}
                <!-- eslint-disable-next-line svelte/no-at-html-tags — DOMPurify-sanitized in markdown.js -->
                {@html renderMarkdown(msg.content)}
              {:else if streaming && i === messages.length - 1 && msg.thinking}
                <span class="text-muted italic">drafting answer…</span>
              {:else if streaming && i === messages.length - 1 && warmupActive}
                <span class="text-muted italic"
                  >warming up {msg.model} into VRAM (cold-start can take ~10s)…</span
                >
              {/if}{#if streaming && i === messages.length - 1}<span
                  class="inline-block w-2 h-4 bg-accent animate-pulse ml-0.5 align-middle"
                ></span>{/if}
            </div>
          {:else}
            <div class="whitespace-pre-wrap text-heading">{msg.content}</div>
          {/if}
          {#if msg.role === 'assistant' && msg.stats?.tokens_per_sec}
            <div
              class="text-xs text-muted font-mono pt-1 cursor-help"
              title="tok/s = writing speed · TTFT = wait before the reply started · tokens = reply length · last number = total time"
            >
              {msg.stats.tokens_per_sec} tok/s · TTFT {msg.stats.ttft_ms}ms · {msg.stats.eval_count} tokens
              · {(msg.stats.total_ms / 1000).toFixed(1)}s
            </div>
          {/if}
        </div>
      {/each}
    </div>

    <div class="border-t border-border bg-surface px-4 py-3">
      <div class="flex gap-2 items-end">
        <textarea
          bind:this={inputEl}
          bind:value={input}
          onkeydown={onKey}
          placeholder={models.length === 0
            ? 'pull a model to start chatting'
            : `message ${selectedModel.value || '…'}`}
          rows="2"
          class="flex-1 bg-surface-2 border border-border rounded px-3 py-2 text-sm resize-none focus:outline-none focus:border-accent text-body"
          disabled={streaming || models.length === 0}
        ></textarea>
        {#if streaming}
          <Button variant="danger" size="lg" onclick={stop} ariaLabel="Stop generation">
            stop
          </Button>
        {:else}
          <Button variant="primary" size="lg" onclick={() => send()} disabled={!input.trim()}>
            send
          </Button>
        {/if}
      </div>
    </div>
  </main>

  <!-- Telemetry sidebar -->
  <aside
    class="w-80 border-l border-border bg-surface overflow-y-auto p-4 text-sm space-y-5 font-mono hidden lg:block"
  >
    <section>
      <h2 class="text-xs uppercase tracking-wider text-muted mb-2">last response</h2>
      {#if liveStat}
        <div class="space-y-1">
          <div class="flex justify-between">
            <span
              class="text-muted cursor-help"
              title="How fast the model writes — tokens generated per second. Higher is faster."
              >tokens/sec</span
            ><span class="text-accent">{liveStat.tokens_per_sec ?? '–'}</span>
          </div>
          <div class="flex justify-between">
            <span
              class="text-muted cursor-help"
              title="Time to first token — the pause before the reply starts. Lower feels snappier."
              >TTFT</span
            ><span>{liveStat.ttft_ms ?? '–'}ms</span>
          </div>
          <div class="flex justify-between">
            <span
              class="text-muted cursor-help"
              title="Tokens are chunks of text — roughly ¾ of a word each. This is how many the reply used."
              >tokens</span
            ><span>{liveStat.eval_count ?? '–'}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted cursor-help" title="Total time to produce the full reply."
              >total</span
            ><span>{liveStat.total_ms ? (liveStat.total_ms / 1000).toFixed(1) + 's' : '–'}</span>
          </div>
        </div>
      {:else}
        <div class="text-muted text-xs">no response yet</div>
      {/if}
    </section>

    <section>
      <h2
        class="text-xs uppercase tracking-wider text-muted mb-2 cursor-help"
        title="Models held in your GPU's memory right now — warmed up and quick to answer."
      >
        loaded in vram
      </h2>
      {#if loaded.length === 0}
        <div class="text-muted text-xs">none</div>
      {:else}
        <div class="space-y-2">
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
      <h2
        class="text-xs uppercase tracking-wider text-muted mb-2 cursor-help"
        title="Your graphics card — local models do their heavy math here."
      >
        gpu
      </h2>
      {#if !gpu || !gpu.available}
        <div class="text-muted text-xs">not available</div>
      {:else}
        {#each gpu.gpus as g (g.name)}
          <div class="space-y-1.5">
            <div class="text-body text-xs truncate">{g.name}</div>
            <div>
              <div class="flex justify-between text-xs mb-0.5">
                <span class="text-muted">vram</span>
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
                <span class="text-muted">util</span>
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
