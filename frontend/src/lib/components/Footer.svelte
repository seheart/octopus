<script>
  import { theme, toggleTheme } from '../stores/theme.svelte.js';
  import { onMount, onDestroy } from 'svelte';
  import { getModels } from '../api.js';

  let connected = $state(false);
  let modelCount = $state(0);
  let pollHandle;

  async function check() {
    try {
      const m = await getModels();
      connected = true;
      modelCount = m.length;
    } catch (_) {
      connected = false;
    }
  }

  onMount(() => {
    check();
    pollHandle = setInterval(check, 5000);
  });

  onDestroy(() => clearInterval(pollHandle));
</script>

<footer class="border-t border-border bg-surface">
  <div class="flex items-center justify-between px-4 py-1.5 text-xs font-mono">
    <div class="flex items-center gap-3">
      <span class="font-semibold text-accent">octopus v0.1</span>
      <span class="text-muted">|</span>
      <span class="flex items-center gap-1.5">
        <span
          class="inline-block w-2 h-2 rounded-full"
          style="background: {connected ? 'var(--success)' : 'var(--error)'};"
        ></span>
        <span class="text-muted">ollama</span>
      </span>
      <span class="text-muted">|</span>
      <span class="text-muted">{modelCount} models</span>
    </div>
    <div class="flex items-center gap-2">
      <button
        onclick={toggleTheme}
        class="px-2 py-0.5 rounded text-muted hover:text-body hover:bg-surface-2 transition-colors"
        title="toggle theme"
        aria-label="Toggle theme"
      >
        {theme.value === 'dark' ? '☀ light' : '☾ dark'}
      </button>
    </div>
  </div>
</footer>
