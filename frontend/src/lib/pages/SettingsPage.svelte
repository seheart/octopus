<script>
  import { theme, setTheme } from '../stores/theme.svelte.js';

  const themes = [
    { id: 'light', label: 'Light', desc: 'Cream paper, ink black' },
    { id: 'dark', label: 'Dark', desc: 'Black canvas, phosphor green' }
  ];
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-3xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-heading mb-1">Settings</h1>
      <p class="text-sm text-muted">Local preferences. Saved to browser storage.</p>
    </div>

    <section class="bg-surface border border-border rounded-lg p-5">
      <h2 class="text-sm font-medium text-heading mb-3">Theme</h2>
      <div class="grid grid-cols-2 gap-2">
        {#each themes as t}
          <button
            onclick={() => setTheme(t.id)}
            class="text-left p-3 rounded border transition-colors
              {theme.value === t.id
                ? 'border-accent bg-surface-2'
                : 'border-border hover:bg-surface-2'}"
          >
            <div class="font-mono text-sm text-heading">{t.label}</div>
            <div class="text-xs text-muted mt-0.5">{t.desc}</div>
          </button>
        {/each}
      </div>
    </section>

    <section class="bg-surface border border-border rounded-lg p-5">
      <h2 class="text-sm font-medium text-heading mb-3">About</h2>
      <div class="text-sm text-muted space-y-1 font-mono">
        <div>octopus v0.1 · model lab</div>
        <div>Backend: FastAPI on :8800</div>
        <div>Frontend: Svelte 5 · Vite · Tailwind 4</div>
        <div>Ollama: 127.0.0.1:11435</div>
      </div>
    </section>
  </div>
</div>
