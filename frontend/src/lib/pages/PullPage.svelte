<script>
  import { onMount } from 'svelte';
  import { getModels, pullModel } from '../api.js';
  import { go } from '../stores/route.svelte.js';
  import { setModel, selectedModel } from '../stores/model.svelte.js';
  import { Button, Card, Section } from '../components/ui/index.js';

  let installed = $state([]);

  let pullName = $state('');
  let pulling = $state(false);
  let pullStatus = $state('');
  let pullPct = $state(null);
  let pullError = $state(null);
  let currentPull = $state(null);

  // Curated suggestions, grouped so people can learn what each family is for.
  // Sizes are approximate — they're educational, not load-bearing.
  const groups = [
    {
      heading: 'general · everyday chat',
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
      heading: 'reasoning · thinks before answering',
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
      heading: 'code · written for programming',
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
      heading: 'embeddings · for search / RAG',
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
      // Non-fatal — just means we can't dim already-installed suggestions.
    }
  }

  onMount(refresh);

  function isInstalled(name) {
    return installed.some((m) => m.name === name || m.name.startsWith(name + ':'));
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
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-5xl mx-auto space-y-6">
    <div class="flex items-baseline gap-3">
      <button
        onclick={() => go('models')}
        class="text-xs font-mono text-muted hover:text-accent transition-colors"
        aria-label="Back to Models"
      >
        ← Models
      </button>
      <h1 class="text-2xl font-bold text-heading">Add a model</h1>
    </div>
    <p class="text-sm text-muted max-w-2xl">
      Pulls from Ollama's registry. Type a model name (e.g. <code
        class="font-mono text-body bg-surface-2 px-1 rounded">qwen3:8b</code
      >) or pick from the suggestions below. Names follow
      <code class="font-mono text-body bg-surface-2 px-1 rounded">family[:tag]</code> — leave the tag
      off for the default.
    </p>

    <Card padding="lg">
      <Section title="pull by name">
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
          <div class="bg-surface-2 border border-border rounded p-3 font-mono text-xs">
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

        <p class="text-xs text-muted mt-3">
          Browse the full catalog at
          <a
            href="https://ollama.com/library"
            target="_blank"
            rel="noopener noreferrer"
            class="text-accent hover:underline">ollama.com/library</a
          >
          — copy any name from there into the box above.
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
                  <span class="text-[10px] uppercase tracking-wider font-mono text-success"
                    >already installed</span
                  >
                {:else}
                  <button
                    onclick={() => startPull(item.name)}
                    disabled={pulling}
                    class="text-xs font-mono text-accent hover:underline disabled:opacity-40 disabled:no-underline"
                  >
                    pull this →
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
