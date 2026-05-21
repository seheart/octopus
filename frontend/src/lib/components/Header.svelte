<script>
  import { onMount, onDestroy } from 'svelte';
  import OctoLogo from './OctoLogo.svelte';
  import { route, go } from '../stores/route.svelte.js';
  import { getLoaded, getGpu } from '../api.js';

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

  // Compact telemetry strip — same data the chat sidebar uses, polled
  // every 3s so it doesn't compete with the activity poller's 250ms tick.
  let loaded = $state([]);
  /** @type {{available:boolean, gpus?: Array<any>} | null} */
  let gpu = $state(null);
  /** @type {ReturnType<typeof setInterval> | undefined} */
  let pollHandle;

  async function refresh() {
    const [l, g] = await Promise.allSettled([getLoaded(), getGpu()]);
    if (l.status === 'fulfilled') loaded = l.value;
    if (g.status === 'fulfilled') gpu = g.value;
  }

  onMount(() => {
    refresh();
    pollHandle = setInterval(refresh, 3000);
  });
  onDestroy(() => clearInterval(pollHandle));

  const primaryGpu = $derived(gpu?.available && gpu.gpus?.[0] ? gpu.gpus[0] : null);
  const vramUsedGb = $derived(primaryGpu ? primaryGpu.memory_used_mb / 1024 : 0);
  const vramTotalGb = $derived(primaryGpu ? primaryGpu.memory_total_mb / 1024 : 0);
  const vramPct = $derived(primaryGpu ? (vramUsedGb / vramTotalGb) * 100 : 0);
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

    <!-- Live system stats — hidden on small screens. -->
    <div
      class="ml-auto hidden md:flex items-center gap-3 text-xs text-muted"
      aria-label="System telemetry"
    >
      <span
        class="whitespace-nowrap cursor-help"
        title="Models held in memory right now, warmed up and ready to respond."
      >
        <span class="text-heading">{loaded.length}</span>
        {loaded.length === 1 ? 'model' : 'models'} loaded
      </span>
      {#if primaryGpu}
        <span aria-hidden="true" class="opacity-50">·</span>
        <span
          class="flex items-center gap-2 whitespace-nowrap cursor-help"
          title="GPU video memory in use by loaded models, out of the total available."
        >
          <span>vram</span>
          <span class="inline-block w-20 h-1.5 bg-surface-2 rounded overflow-hidden align-middle">
            <span class="block h-full bg-accent" style="width: {vramPct.toFixed(1)}%"></span>
          </span>
          <span class="text-heading">
            {vramUsedGb.toFixed(1)}/{vramTotalGb.toFixed(0)} GB
          </span>
        </span>
        <span aria-hidden="true" class="opacity-50">·</span>
        <span
          class="whitespace-nowrap cursor-help"
          title="GPU utilization — how busy the graphics card is, near 100% while generating."
        >
          util <span class="text-heading">{primaryGpu.utilization_pct}%</span>
        </span>
        <span aria-hidden="true" class="opacity-50">·</span>
        <span class="whitespace-nowrap text-heading">{primaryGpu.temp_c}°C</span>
      {/if}
    </div>
  </div>
</header>
