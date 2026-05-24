<script>
  import { connection } from '../stores/connection.svelte.js';
  import { go } from '../stores/route.svelte.js';
</script>

{#if !connection.ok}
  <div
    role="alert"
    class="bg-error text-canvas px-4 py-1.5 text-xs flex items-center justify-between gap-3"
  >
    <span> Octopus can't reach Ollama on this machine. Is Ollama running? </span>
    <div class="flex items-center gap-2 shrink-0">
      <button
        onclick={() => go('diagnostic')}
        class="bg-transparent border border-canvas/40 text-canvas hover:bg-canvas/10 transition-colors px-2 py-0.5 rounded text-[11px] font-medium cursor-pointer"
      >
        Diagnose →
      </button>
      <span class="opacity-70 font-mono">retrying…</span>
    </div>
  </div>
{/if}
