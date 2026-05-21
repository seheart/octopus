<script>
  import { connection } from '../stores/connection.svelte.js';
</script>

{#if !connection.backend}
  <div
    role="alert"
    class="bg-error text-canvas px-4 py-1.5 text-xs font-mono flex items-center justify-between"
  >
    <span>
      Backend unreachable. Check that the FastAPI server is running on
      <span class="font-bold">port 8800</span> (run <span class="font-bold">./start.sh</span>).
    </span>
    <span class="opacity-70">retrying…</span>
  </div>
{:else if !connection.ollama}
  <div
    role="alert"
    class="bg-warning text-canvas px-4 py-1.5 text-xs font-mono flex items-center justify-between"
  >
    <span>
      Ollama isn't running. Start it with <span class="font-bold">ollama serve</span> — Octopus connects
      automatically once it's up.
    </span>
    <span class="opacity-70">waiting…</span>
  </div>
{/if}
