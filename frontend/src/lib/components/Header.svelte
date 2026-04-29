<script>
  import OctoLogo from './OctoLogo.svelte';
  import { route, go } from '../stores/route.svelte.js';

  const primaryTabs = [
    { id: 'chat', label: 'Chat' },
    { id: 'models', label: 'Models' },
    { id: 'roadmap', label: 'Roadmap' }
  ];
</script>

<header class="border-b border-border bg-surface">
  <div class="flex items-center px-4 py-2 gap-4">
    <button
      onclick={() => go('chat')}
      class="flex items-baseline gap-2 hover:opacity-80 transition-opacity"
      aria-label="Octopus home"
    >
      <OctoLogo size={20} />
      <span class="text-lg font-bold text-heading tracking-tight">octopus</span>
      <span class="text-xs text-muted font-mono hidden sm:inline">model lab</span>
    </button>

    <nav class="flex items-center gap-1 ml-4 flex-1" aria-label="Primary">
      {#each primaryTabs as tab (tab.id)}
        <button
          onclick={() => go(tab.id)}
          class="px-3 py-1.5 text-sm rounded transition-colors
            {route.page === tab.id
            ? 'bg-surface-2 text-heading font-medium'
            : 'text-muted hover:text-body hover:bg-surface-2'}">{tab.label}</button
        >
      {/each}
    </nav>

    <button
      onclick={() => go('settings')}
      class="px-3 py-1.5 text-sm rounded transition-colors
        {route.page === 'settings'
        ? 'bg-surface-2 text-heading font-medium'
        : 'text-muted hover:text-body hover:bg-surface-2'}"
      aria-label="Settings"
    >
      Settings
    </button>
  </div>
</header>
