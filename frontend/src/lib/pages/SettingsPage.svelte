<script>
  import { theme, setTheme } from '../stores/theme.svelte.js';
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
    { id: 'dark', label: 'Dark', desc: 'Black canvas, phosphor green' }
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
      <Section title="default chat model">
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
      <Section title="theme">
        <p class="text-xs text-muted mb-2">Also togglable from the moon/sun icon in the footer.</p>
        <div class="grid grid-cols-2 gap-2">
          {#each themes as t (t.id)}
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
      </Section>
    </Card>

    <!-- Storage info -->
    <Card padding="lg">
      <Section title="local data">
        <p class="text-xs text-muted leading-relaxed">
          Octopus stores theme + default-model in your browser's localStorage. There is no server
          state, no telemetry, and no account. Clearing site data resets these to defaults.
        </p>
      </Section>
    </Card>
  </div>
</div>
