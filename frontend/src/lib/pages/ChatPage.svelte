<script>
  import { onMount, onDestroy } from 'svelte';
  import { getModels, getLoaded, getGpu, fmtBytes, fmtParams } from '../api.js';

  let models = $state([]);
  let model = $state('');
  let messages = $state([]);
  let input = $state('');
  let streaming = $state(false);
  let liveStat = $state(null);
  let loaded = $state([]);
  let gpu = $state(null);
  let scrollEl;
  let pollHandle;

  onMount(async () => {
    await loadModels();
    await refresh();
    pollHandle = setInterval(refresh, 2000);
  });

  onDestroy(() => clearInterval(pollHandle));

  async function loadModels() {
    try {
      const all = await getModels();
      models = all.filter(m => !m.name.includes('embed'));
      if (!model && models.length) model = models[0].name;
    } catch (_) { /* offline */ }
  }

  async function refresh() {
    try {
      [loaded, gpu] = await Promise.all([getLoaded(), getGpu()]);
    } catch (_) { /* ignore */ }
  }

  async function send() {
    if (!input.trim() || streaming || !model) return;
    const userMsg = { role: 'user', content: input.trim() };
    const asstMsg = { role: 'assistant', content: '', model, stats: {} };
    messages = [...messages, userMsg, asstMsg];
    input = '';
    streaming = true;
    liveStat = null;
    scrollToBottom();

    const conv = messages
      .filter(m => m.role !== 'assistant' || m.content)
      .map(m => ({ role: m.role, content: m.content }));

    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ model, messages: conv })
    });

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
        const line = block.split('\n').find(l => l.startsWith('data: '));
        if (!line) continue;
        const evt = JSON.parse(line.slice(6));
        const last = messages[messages.length - 1];
        if (evt.type === 'token') {
          last.content += evt.content;
          messages = [...messages.slice(0, -1), last];
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
        }
      }
    }
    streaming = false;
    refresh();
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
</script>

<div class="h-full flex overflow-hidden">
  <!-- Chat panel -->
  <main class="flex-1 flex flex-col overflow-hidden">
    <div class="px-4 py-2 border-b border-border bg-surface flex items-center justify-between gap-3">
      <select
        bind:value={model}
        class="bg-surface-2 text-body border border-border rounded px-2 py-1 text-sm font-mono focus:outline-none focus:border-accent"
      >
        {#each models as m}
          <option value={m.name}>{m.name} · {fmtParams(m.details?.parameter_size)}</option>
        {/each}
      </select>
      <button
        onclick={clearChat}
        class="text-xs text-muted hover:text-body px-2 py-1 border border-border rounded"
      >clear</button>
    </div>

    <div bind:this={scrollEl} class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      {#if messages.length === 0}
        <div class="text-muted text-sm h-full flex items-center justify-center">
          <div class="text-center font-mono">
            pick a model · ask anything
          </div>
        </div>
      {/if}
      {#each messages as msg, i (i)}
        <div class="flex flex-col gap-1">
          <div class="text-xs text-muted font-mono uppercase tracking-wide">
            {msg.role === 'user' ? 'you' : (msg.model || 'assistant')}
          </div>
          <div
            class="whitespace-pre-wrap text-body"
            class:text-heading={msg.role === 'user'}
          >{msg.content}{#if streaming && i === messages.length - 1}<span class="inline-block w-2 h-4 bg-accent animate-pulse ml-0.5"></span>{/if}</div>
          {#if msg.role === 'assistant' && msg.stats?.tokens_per_sec}
            <div class="text-xs text-muted font-mono pt-1">
              {msg.stats.tokens_per_sec} tok/s
              · TTFT {msg.stats.ttft_ms}ms
              · {msg.stats.eval_count} tokens
              · {(msg.stats.total_ms / 1000).toFixed(1)}s
            </div>
          {/if}
        </div>
      {/each}
    </div>

    <div class="border-t border-border bg-surface px-4 py-3">
      <div class="flex gap-2 items-end">
        <textarea
          bind:value={input}
          onkeydown={onKey}
          placeholder="message {model || '…'}"
          rows="2"
          class="flex-1 bg-surface-2 border border-border rounded px-3 py-2 text-sm resize-none focus:outline-none focus:border-accent text-body"
          disabled={streaming}
        ></textarea>
        <button
          onclick={send}
          disabled={streaming || !input.trim()}
          class="bg-accent text-canvas font-medium px-4 py-2 rounded text-sm disabled:opacity-40 hover:opacity-90"
        >{streaming ? '…' : 'send'}</button>
      </div>
    </div>
  </main>

  <!-- Telemetry sidebar -->
  <aside class="w-80 border-l border-border bg-surface overflow-y-auto p-4 text-sm space-y-5 font-mono">
    <section>
      <h2 class="text-xs uppercase tracking-wider text-muted mb-2">last response</h2>
      {#if liveStat}
        <div class="space-y-1">
          <div class="flex justify-between"><span class="text-muted">tokens/sec</span><span class="text-accent">{liveStat.tokens_per_sec ?? '–'}</span></div>
          <div class="flex justify-between"><span class="text-muted">TTFT</span><span>{liveStat.ttft_ms ?? '–'}ms</span></div>
          <div class="flex justify-between"><span class="text-muted">tokens</span><span>{liveStat.eval_count ?? '–'}</span></div>
          <div class="flex justify-between"><span class="text-muted">total</span><span>{liveStat.total_ms ? (liveStat.total_ms / 1000).toFixed(1) + 's' : '–'}</span></div>
        </div>
      {:else}
        <div class="text-muted text-xs">no response yet</div>
      {/if}
    </section>

    <section>
      <h2 class="text-xs uppercase tracking-wider text-muted mb-2">loaded in vram</h2>
      {#if loaded.length === 0}
        <div class="text-muted text-xs">none</div>
      {:else}
        <div class="space-y-2">
          {#each loaded as m}
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
      <h2 class="text-xs uppercase tracking-wider text-muted mb-2">gpu</h2>
      {#if !gpu || !gpu.available}
        <div class="text-muted text-xs">not available</div>
      {:else}
        {#each gpu.gpus as g}
          <div class="space-y-1.5">
            <div class="text-body text-xs truncate">{g.name}</div>
            <div>
              <div class="flex justify-between text-xs mb-0.5">
                <span class="text-muted">vram</span>
                <span>{(g.memory_used_mb / 1024).toFixed(1)} / {(g.memory_total_mb / 1024).toFixed(0)} GB</span>
              </div>
              <div class="h-1.5 bg-surface-2 rounded overflow-hidden">
                <div class="h-full bg-accent" style="width: {(g.memory_used_mb / g.memory_total_mb * 100).toFixed(1)}%"></div>
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
