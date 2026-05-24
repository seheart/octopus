<script>
  import { onMount } from 'svelte';
  import { getModels, pullModel, fmtBytes } from '../api.js';
  import { setModel, selectedModel } from '../stores/model.svelte.js';
  import { Button, Card, Section } from '../components/ui/index.js';

  let installed = $state([]);

  let pullName = $state('');
  let pulling = $state(false);
  let pullStatus = $state('');
  let pullPct = $state(null);
  let pullTotal = $state(null);
  let pullCompleted = $state(null);
  let pullError = $state(null);
  let currentPull = $state(null);

  // Track bytes/sec with a small rolling sample so the ETA isn't jittery.
  let lastSample = $state({ at: 0, bytes: 0 });
  let bytesPerSec = $state(0);

  const groups = [
    {
      heading: 'General · everyday chat',
      tip: 'Good defaults. Quick to load, decent quality.',
      items: [
        {
          name: 'llama3.2:3b',
          size: '~2 GB',
          desc: 'Tiny, fast, surprisingly capable. Great first model on modest hardware.'
        },
        {
          name: 'llama3.1:8b',
          size: '~4.7 GB',
          desc: 'The reliable workhorse. Strong general chat at mid size.'
        },
        {
          name: 'mistral:7b',
          size: '~4.1 GB',
          desc: 'Classic open-weight model. Snappy, less verbose than llama.'
        },
        {
          name: 'phi4',
          size: '~9 GB',
          desc: "Microsoft's 14B model. Punches above its weight on reasoning."
        },
        {
          name: 'gemma3:12b',
          size: '~9 GB',
          desc: "Google's mid-size. Strong instruction following."
        }
      ]
    },
    {
      heading: 'Reasoning · thinks before answering',
      tip: 'Streams a "thinking" trace before the answer. Slower, but better at multi-step problems.',
      items: [
        {
          name: 'qwen3:8b',
          size: '~5 GB',
          desc: 'Alibaba reasoning model. Smaller, fits more places.'
        },
        {
          name: 'qwen3:14b',
          size: '~9 GB',
          desc: 'Bigger qwen3. Better reasoning, slower.'
        },
        {
          name: 'deepseek-r1:14b',
          size: '~9 GB',
          desc: 'DeepSeek reasoning. Strong on math + code problems.'
        }
      ]
    },
    {
      heading: 'Code · written for programming',
      tip: 'Tuned on code corpora — better at completing, explaining, and refactoring.',
      items: [
        {
          name: 'qwen2.5-coder:7b',
          size: '~4.7 GB',
          desc: 'Solid code model. Good at multi-file context.'
        },
        {
          name: 'codellama:13b',
          size: '~7 GB',
          desc: "Meta's code llama. Older but proven."
        }
      ]
    },
    {
      heading: 'Embeddings · for search / RAG',
      tip: "These don't chat — they convert text to vectors. Use them when you're building search.",
      items: [
        {
          name: 'nomic-embed-text',
          size: '~270 MB',
          desc: 'High-quality general embeddings. The default pick for RAG.'
        },
        {
          name: 'mxbai-embed-large',
          size: '~670 MB',
          desc: 'Bigger embedding model. Slightly better recall.'
        }
      ]
    }
  ];

  async function refresh() {
    try {
      installed = await getModels();
    } catch (_e) {
      /* non-fatal */
    }
  }

  onMount(refresh);

  function isInstalled(name) {
    return installed.some((m) => m.name === name || m.name.startsWith(name + ':'));
  }

  // Translate Ollama's wire-level status strings to user-facing phases.
  function friendlyStatus(raw) {
    if (!raw) return '';
    const s = raw.toLowerCase();
    if (s.includes('pulling manifest')) return 'Looking up model…';
    if (s.includes('verifying')) return 'Checking integrity…';
    if (s.includes('writing manifest')) return 'Finishing up…';
    if (s === 'success' || s === 'done') return 'Installed.';
    if (s.startsWith('pulling ') || s.startsWith('downloading')) return 'Downloading…';
    if (s === 'starting…') return 'Starting…';
    return raw;
  }

  function fmtEta(seconds) {
    if (!isFinite(seconds) || seconds <= 0) return '';
    if (seconds < 60) return `${Math.round(seconds)}s left`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return s ? `${m}m ${s}s left` : `${m}m left`;
  }

  async function startPull(name = pullName) {
    const target = name.trim();
    if (!target || pulling) return;
    pulling = true;
    pullStatus = 'starting…';
    pullPct = null;
    pullTotal = null;
    pullCompleted = null;
    pullError = null;
    pullName = target;
    bytesPerSec = 0;
    lastSample = { at: Date.now(), bytes: 0 };

    try {
      currentPull = pullModel(target, (evt) => {
        if (evt.status === 'error') {
          pullError = evt.error || 'install failed';
          return;
        }
        pullStatus = evt.status;
        if (typeof evt.total === 'number') pullTotal = evt.total;
        if (typeof evt.completed === 'number') {
          pullCompleted = evt.completed;
          if (pullTotal) pullPct = Math.min(100, (pullCompleted / pullTotal) * 100);
          // Bytes/sec EMA over a ~3s window for ETA smoothing.
          const now = Date.now();
          const dtMs = now - lastSample.at;
          if (dtMs > 300) {
            const inst = ((pullCompleted - lastSample.bytes) / dtMs) * 1000;
            bytesPerSec = bytesPerSec ? bytesPerSec * 0.7 + inst * 0.3 : inst;
            lastSample = { at: now, bytes: pullCompleted };
          }
        }
      });
      await currentPull.done;
      if (!pullError) {
        pullStatus = 'success';
        await refresh();
        if (!selectedModel.value) setModel(target);
      }
    } catch (e) {
      if (e.name !== 'AbortError') pullError = e.message;
    } finally {
      pulling = false;
      currentPull = null;
    }
  }

  function cancelPull() {
    currentPull?.abort();
  }

  function onPullKey(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      startPull();
    }
  }

  const etaSeconds = $derived(
    pulling && bytesPerSec > 0 && pullTotal && pullCompleted !== null
      ? (pullTotal - pullCompleted) / bytesPerSec
      : 0
  );
  const friendly = $derived(friendlyStatus(pullStatus));
  const isDone = $derived(pullStatus === 'success' || pullStatus === 'done');
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-5xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-heading">Install a model</h1>
      <p class="text-sm text-muted mt-1 max-w-2xl">
        Pick one from below, or type the name of any model from
        <a
          href="https://ollama.com/library"
          target="_blank"
          rel="noopener noreferrer"
          class="text-accent hover:underline">ollama.com/library</a
        >. Downloads run in the background and you can keep using the app.
      </p>
    </div>

    <Card padding="lg">
      <Section title="Install by name">
        <div class="flex gap-2 items-center mb-3">
          <input
            type="text"
            bind:value={pullName}
            onkeydown={onPullKey}
            placeholder="e.g. qwen3:8b, llama3.2:3b"
            disabled={pulling}
            class="flex-1 bg-surface-2 border border-border rounded px-3 py-1.5 text-sm font-mono focus:outline-none focus:border-accent text-body disabled:opacity-50"
            aria-label="Model name to install"
          />
          {#if pulling}
            <Button variant="secondary" onclick={cancelPull}>Cancel</Button>
          {:else}
            <Button variant="primary" onclick={() => startPull()} disabled={!pullName.trim()}>
              Install
            </Button>
          {/if}
        </div>

        {#if pulling || pullError || isDone}
          <div class="bg-surface-2 border border-border rounded p-3 font-mono text-xs space-y-1.5">
            <div class="flex justify-between gap-3">
              <span class="text-body truncate">{pullName || '—'}</span>
              <span class="text-muted shrink-0">
                {#if pullError}
                  <span class="text-error">{pullError}</span>
                {:else if isDone}
                  <span class="text-success">✓ Installed</span>
                {:else}
                  {friendly}
                {/if}
              </span>
            </div>
            {#if pullPct !== null && !pullError && !isDone}
              <div class="h-1.5 bg-canvas rounded overflow-hidden">
                <div class="h-full bg-accent transition-all" style="width: {pullPct}%"></div>
              </div>
              <div class="flex justify-between text-muted">
                <span>
                  {pullPct.toFixed(0)}%
                  {#if pullCompleted !== null && pullTotal}
                    · {fmtBytes(pullCompleted)} / {fmtBytes(pullTotal)}
                  {/if}
                </span>
                <span>
                  {#if bytesPerSec > 0}
                    {fmtBytes(bytesPerSec)}/s
                  {/if}
                  {#if etaSeconds > 0}
                    · {fmtEta(etaSeconds)}
                  {/if}
                </span>
              </div>
            {/if}
          </div>
        {/if}

        <p class="text-xs text-muted mt-3">
          Names follow <code class="font-mono text-body bg-surface-2 px-1 rounded"
            >family[:tag]</code
          >
          — leave the tag off to get the default. Browse the catalog at
          <a
            href="https://ollama.com/library"
            target="_blank"
            rel="noopener noreferrer"
            class="text-accent hover:underline">ollama.com/library</a
          >.
        </p>
      </Section>
    </Card>

    {#each groups as group (group.heading)}
      <div>
        <div class="text-xs font-mono text-muted uppercase tracking-wider mb-1">
          {group.heading}
        </div>
        <p class="text-xs text-muted mb-3">{group.tip}</p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          {#each group.items as item (item.name)}
            {@const installed = isInstalled(item.name)}
            <div
              class="bg-surface border border-border rounded-lg p-4 flex flex-col gap-2 hover:border-accent transition-colors"
            >
              <div class="flex items-baseline justify-between gap-2">
                <div class="font-mono text-sm text-heading font-medium truncate">{item.name}</div>
                <span class="text-[10px] font-mono text-muted shrink-0">{item.size}</span>
              </div>
              <p class="text-sm text-body leading-snug">{item.desc}</p>
              <div class="mt-auto pt-1">
                {#if installed}
                  <span
                    class="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider font-mono text-success"
                  >
                    <span class="w-1.5 h-1.5 rounded-full bg-success" aria-hidden="true"></span>
                    Installed
                  </span>
                {:else}
                  <button
                    onclick={() => startPull(item.name)}
                    disabled={pulling}
                    class="text-xs font-medium text-accent hover:underline disabled:opacity-40 disabled:no-underline bg-transparent border-0 p-0 cursor-pointer"
                  >
                    Install →
                  </button>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  </div>
</div>
