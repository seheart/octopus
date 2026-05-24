<script>
  // Cmd/Ctrl+K command palette — pages, model switch, theme. Type to filter,
  // arrow keys to navigate, Enter to commit, Esc to close. Single source of
  // discoverability for the keyboard-driven user; visible from anywhere.

  import { onMount, onDestroy, tick } from 'svelte';
  import { go } from '../stores/route.svelte.js';
  import { setModel, selectedModel } from '../stores/model.svelte.js';
  import { setThemeMode } from '../stores/theme.svelte.js';
  import { getModels } from '../api.js';

  let open = $state(false);
  let query = $state('');
  let highlight = $state(0);
  /** @type {HTMLInputElement | undefined} */
  let inputEl = $state();
  let models = $state([]);

  const pages = [
    { id: 'p:chat', label: 'Chat', kind: 'Page', action: () => go('chat') },
    { id: 'p:models', label: 'Models', kind: 'Page', action: () => go('models') },
    { id: 'p:pull', label: 'Install a model', kind: 'Page', action: () => go('pull') },
    { id: 'p:storage', label: 'Storage', kind: 'Page', action: () => go('storage') },
    { id: 'p:system', label: 'System', kind: 'Page', action: () => go('system') },
    { id: 'p:diagnostic', label: 'Diagnostic', kind: 'Page', action: () => go('diagnostic') },
    { id: 'p:settings', label: 'Settings', kind: 'Page', action: () => go('settings') }
  ];

  const actions = [
    {
      id: 'a:theme-light',
      label: 'Theme: Light',
      kind: 'Action',
      action: () => setThemeMode('light')
    },
    {
      id: 'a:theme-dark',
      label: 'Theme: Dark',
      kind: 'Action',
      action: () => setThemeMode('dark')
    },
    {
      id: 'a:theme-system',
      label: 'Theme: Match system',
      kind: 'Action',
      action: () => setThemeMode('system')
    }
  ];

  const modelItems = $derived(
    models.map((m) => ({
      id: 'm:' + m.name,
      label: m.name,
      kind: 'Switch to model',
      action: () => {
        setModel(m.name);
        go('chat');
      }
    }))
  );

  const allItems = $derived([...pages, ...modelItems, ...actions]);

  function score(item, q) {
    if (!q) return 1;
    const lower = item.label.toLowerCase();
    const needle = q.toLowerCase();
    if (lower.startsWith(needle)) return 3;
    if (lower.includes(needle)) return 2;
    // Loose substring: every char in order
    let j = 0;
    for (let i = 0; i < lower.length && j < needle.length; i++) {
      if (lower[i] === needle[j]) j++;
    }
    return j === needle.length ? 1 : 0;
  }

  const filtered = $derived(
    allItems
      .map((item) => ({ item, s: score(item, query) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .map((x) => x.item)
  );

  async function show() {
    if (open) return;
    try {
      models = (await getModels()).filter((m) => !m.name.includes('embed'));
    } catch (_) {
      models = [];
    }
    open = true;
    query = '';
    highlight = 0;
    await tick();
    inputEl?.focus();
  }

  function hide() {
    open = false;
  }

  function run(item) {
    item?.action?.();
    hide();
  }

  function onGlobalKey(e) {
    // Cmd+K / Ctrl+K toggles
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      open ? hide() : show();
      return;
    }
    if (!open) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      hide();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      highlight = Math.min(highlight + 1, filtered.length - 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      highlight = Math.max(highlight - 1, 0);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      run(filtered[highlight]);
    }
  }

  // Clamp highlight when filter shrinks (e.g. you type more chars).
  $effect(() => {
    if (highlight >= filtered.length) highlight = Math.max(0, filtered.length - 1);
  });

  onMount(() => window.addEventListener('keydown', onGlobalKey));
  onDestroy(() => window.removeEventListener('keydown', onGlobalKey));
</script>

{#if open}
  <!-- Overlay: dismiss on click outside the panel. -->
  <div
    role="presentation"
    onclick={hide}
    class="fixed inset-0 z-50 bg-canvas/60 backdrop-blur-sm flex items-start justify-center pt-[15vh] px-4"
  >
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      tabindex="-1"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
      class="w-full max-w-xl bg-surface border border-border rounded-lg shadow-lg overflow-hidden"
    >
      <input
        bind:this={inputEl}
        bind:value={query}
        placeholder="Jump to a page, switch model, change theme…"
        class="w-full bg-transparent border-0 border-b border-border px-4 py-3 text-sm font-mono focus:outline-none text-body placeholder:text-muted"
        aria-label="Command palette input"
      />
      <div class="max-h-[50vh] overflow-y-auto py-1">
        {#if filtered.length === 0}
          <div class="px-4 py-6 text-sm text-muted text-center">No matches.</div>
        {:else}
          {#each filtered as item, i (item.id)}
            {@const isCurrentModel = item.id === 'm:' + selectedModel.value}
            <button
              onclick={() => run(item)}
              onmouseenter={() => (highlight = i)}
              class="w-full flex items-center justify-between gap-3 px-4 py-2 text-left text-sm cursor-pointer transition-colors {highlight ===
              i
                ? 'bg-surface-2'
                : 'bg-transparent hover:bg-surface-2'}"
            >
              <span class="text-body font-mono truncate">{item.label}</span>
              <span class="text-[10px] text-muted uppercase tracking-wider font-mono shrink-0">
                {isCurrentModel ? 'current' : item.kind}
              </span>
            </button>
          {/each}
        {/if}
      </div>
      <div
        class="border-t border-border px-4 py-1.5 text-[10px] font-mono text-muted flex justify-between"
      >
        <span>↑↓ navigate · ↵ select · Esc close</span>
        <span>⌘K</span>
      </div>
    </div>
  </div>
{/if}
