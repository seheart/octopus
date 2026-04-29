<script>
  import { theme, toggleTheme } from '../stores/theme.svelte.js';
  import { route, go } from '../stores/route.svelte.js';
  import { onMount, onDestroy } from 'svelte';
  import { getModels } from '../api.js';

  let connected = $state(false);
  let modelCount = $state(0);
  /** @type {ReturnType<typeof setInterval> | undefined} */
  let pollHandle;

  async function check() {
    try {
      const m = await getModels();
      connected = true;
      modelCount = m.length;
    } catch (_e) {
      connected = false;
    }
  }

  onMount(() => {
    check();
    pollHandle = setInterval(check, 5000);
  });

  onDestroy(() => clearInterval(pollHandle));

  /** @type {string} */
  const githubUrl = 'https://github.com/seheart/octopus';

  const isDark = $derived(theme.value === 'dark');
</script>

<footer class="border-t border-border bg-surface">
  <div class="grid grid-cols-3 items-center px-4 py-1.5 text-xs font-mono gap-4">
    <!-- Left: status -->
    <div class="flex items-center gap-3 justify-self-start">
      <span class="font-semibold text-accent">octopus v0.1</span>
      <span class="text-muted" aria-hidden="true">|</span>
      <span
        class="flex items-center gap-1.5"
        title={connected ? 'Ollama connected' : 'Ollama unreachable'}
      >
        <span
          class="inline-block w-2 h-2 rounded-full"
          style={connected ? 'background: var(--success);' : 'background: var(--error);'}
          aria-hidden="true"
        ></span>
        <span class="text-muted">ollama</span>
      </span>
      <span class="text-muted" aria-hidden="true">|</span>
      <span class="text-muted">{modelCount} models</span>
    </div>

    <!-- Center: secondary nav -->
    <nav class="flex items-center gap-3 justify-self-center" aria-label="Footer navigation">
      <button
        onclick={() => go('system')}
        class="bg-transparent border-0 p-0 cursor-pointer transition-colors
          {route.page === 'system' ? 'text-accent' : 'text-muted hover:text-accent'}"
        aria-label="System page"
      >
        System
      </button>
      <span class="text-muted" aria-hidden="true">|</span>
      <button
        onclick={() => go('design')}
        class="bg-transparent border-0 p-0 cursor-pointer transition-colors
          {route.page === 'design' ? 'text-accent' : 'text-muted hover:text-accent'}"
        aria-label="Design system page"
      >
        Design
      </button>
      <span class="text-muted" aria-hidden="true">|</span>
      <button
        onclick={() => go('roadmap')}
        class="bg-transparent border-0 p-0 cursor-pointer transition-colors
          {route.page === 'roadmap' ? 'text-accent' : 'text-muted hover:text-accent'}"
        aria-label="Roadmap page"
      >
        Roadmap
      </button>
    </nav>

    <!-- Right: GitHub + theme toggle -->
    <div class="flex items-center gap-2 justify-self-end">
      <a
        href={githubUrl}
        target="_blank"
        rel="noopener noreferrer"
        class="text-muted hover:text-accent transition-colors no-underline flex items-center p-1"
        title="GitHub"
        aria-label="View source on GitHub"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56 0-.27-.01-1-.02-1.96-3.2.7-3.87-1.54-3.87-1.54-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.75 2.68 1.25 3.34.95.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.7 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.05 0 0 .96-.31 3.15 1.18a10.9 10.9 0 0 1 5.74 0c2.19-1.49 3.15-1.18 3.15-1.18.62 1.59.23 2.76.11 3.05.74.81 1.18 1.84 1.18 3.1 0 4.43-2.69 5.41-5.25 5.69.41.36.78 1.07.78 2.15 0 1.55-.01 2.81-.01 3.19 0 .31.21.68.8.56C20.22 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5z"
          />
        </svg>
      </a>
      <button
        onclick={toggleTheme}
        class="text-muted hover:text-accent transition-colors bg-transparent border-0 p-1 cursor-pointer flex items-center"
        title="Switch to {isDark ? 'light' : 'dark'} theme"
        aria-label="Switch to {isDark ? 'light' : 'dark'} theme"
      >
        {#if isDark}
          <!-- sun -->
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
            <circle cx="12" cy="12" r="5" />
            <line x1="12" y1="1" x2="12" y2="3" />
            <line x1="12" y1="21" x2="12" y2="23" />
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
            <line x1="1" y1="12" x2="3" y2="12" />
            <line x1="21" y1="12" x2="23" y2="12" />
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
          </svg>
        {:else}
          <!-- moon -->
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
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        {/if}
      </button>
    </div>
  </div>
</footer>
