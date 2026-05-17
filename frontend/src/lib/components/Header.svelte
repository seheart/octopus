<script>
  import OctoLogo from './OctoLogo.svelte';
  import { route, go } from '../stores/route.svelte.js';

  const primaryTabs = [
    { id: 'chat', label: 'chat' },
    { id: 'models', label: 'models' }
  ];

  function navClass(id) {
    const active = route.page === id;
    return `bg-transparent border-0 p-0 cursor-pointer transition-colors whitespace-nowrap ${
      active
        ? 'text-accent underline underline-offset-4 decoration-1'
        : 'text-muted hover:text-accent'
    }`;
  }
</script>

<header class="border-b border-border bg-surface">
  <div class="flex items-center px-4 py-3 gap-6 font-mono text-sm">
    <button
      onclick={() => go('chat')}
      class="flex items-center gap-2 bg-transparent border-0 p-0 cursor-pointer text-heading hover:opacity-80 transition-opacity"
      aria-label="Octopus home"
    >
      <OctoLogo size={18} />
      <span class="font-medium tracking-tight">octopus</span>
    </button>

    <nav class="flex items-center gap-5" aria-label="Primary">
      {#each primaryTabs as tab (tab.id)}
        <button
          onclick={() => go(tab.id)}
          aria-current={route.page === tab.id ? 'page' : undefined}
          class={navClass(tab.id)}
        >
          {tab.label}
        </button>
      {/each}
    </nav>
  </div>
</header>
