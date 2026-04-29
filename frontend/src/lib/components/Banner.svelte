<script>
  import { connection } from '../stores/connection.svelte.js';
</script>

{#if !connection.ok}
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
{/if}
