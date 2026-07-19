<script>
  import { theme, setThemeMode } from '../stores/theme.svelte.js';
  import { selectedModel, setModel } from '../stores/model.svelte.js';
  import { Card, Section } from '../components/ui/index.js';
  import { onMount } from 'svelte';
  import { getModels } from '../api.js';

  let models = $state([]);

  onMount(async () => {
    try {
      models = (await getModels()).filter((m) => !m.name.includes('embed'));
    } catch (_e) {
      /* ignore */
    }
  });

  const themes = [
    { id: 'light', label: 'Light', desc: 'Cream paper, ink black' },
    { id: 'dark', label: 'Dark', desc: 'Black canvas, phosphor green' },
    { id: 'system', label: 'Match system', desc: 'Follows your OS preference, live' }
  ];

  const shortcuts = [
    { keys: '⌘K / Ctrl+K', desc: 'Command palette — jump anywhere' },
    { keys: '⌘N / Ctrl+N', desc: 'New chat (clears the current thread)' },
    { keys: 'Enter', desc: 'Send message' },
    { keys: 'Shift+Enter', desc: 'New line in the message' },
    { keys: 'Esc (in palette)', desc: 'Close the command palette' }
  ];
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-3xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-heading mb-1">Settings</h1>
      <p class="text-sm text-muted">Local preferences. Saved to browser storage.</p>
    </div>

    <!-- Default model -->
    <Card padding="lg">
      <Section title="Default chat model">
        <p class="text-xs text-muted mb-2">
          Pre-selected when you open Chat. You can still switch from the dropdown there.
        </p>
        <select
          value={selectedModel.value}
          onchange={(e) => setModel(e.currentTarget.value)}
          class="bg-surface-2 text-body border border-border rounded px-3 py-1.5 text-sm font-mono focus:outline-none focus:border-accent w-full max-w-md"
        >
          {#if models.length === 0}
            <option value="">— no models installed —</option>
          {/if}
          {#each models as m (m.name)}
            <option value={m.name}>{m.name}</option>
          {/each}
        </select>
      </Section>
    </Card>

    <!-- Theme -->
    <Card padding="lg">
      <Section title="Theme">
        <p class="text-xs text-muted mb-2">
          The footer icon toggles light/dark — pick "Match system" here if you want it to follow
          your OS instead.
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {#each themes as t (t.id)}
            <button
              onclick={() => setThemeMode(t.id)}
              class="text-left p-3 rounded border transition-colors
                {theme.mode === t.id
                ? 'border-accent bg-surface-2'
                : 'border-border hover:bg-surface-2'}"
              aria-pressed={theme.mode === t.id}
            >
              <div class="font-mono text-sm text-heading">{t.label}</div>
              <div class="text-xs text-muted mt-0.5">{t.desc}</div>
            </button>
          {/each}
        </div>
      </Section>
    </Card>

    <!-- Keyboard shortcuts -->
    <Card padding="lg">
      <Section title="Keyboard shortcuts">
        <div class="space-y-1.5 text-sm">
          {#each shortcuts as s (s.keys)}
            <div class="flex items-baseline justify-between gap-3 font-mono text-xs">
              <span class="text-muted">{s.desc}</span>
              <kbd class="bg-surface-2 border border-border px-1.5 py-0.5 rounded text-body"
                >{s.keys}</kbd
              >
            </div>
          {/each}
        </div>
      </Section>
    </Card>

    <!-- Storage info -->
    <Card padding="lg">
      <Section title="Local data">
        <p class="text-xs text-muted leading-relaxed">
          Octopus saves your theme and default model in this browser. No accounts, no servers, no
          tracking. Clear site data to reset.
        </p>
      </Section>
    </Card>
  </div>
</div>
