<script>
  import { go } from '../stores/route.svelte.js';
  import { setPendingPull } from '../stores/model.svelte.js';
  import { Button } from './ui/index.js';

  /**
   * GetStarted — the first-run guide. Two steps that each check themselves
   * off as the user satisfies them:
   *   ① start Ollama   ② pull a model
   * ModelsPage and ChatPage render this whenever either step is unmet, so a
   * fresh user (no `ollama serve`, no models) sees a path instead of an error.
   *
   * @typedef {Object} Props
   * @property {boolean} [ollamaReachable] - is `ollama serve` up
   * @property {boolean} [hasModels] - is at least one model installed
   */

  /** @type {Props} */
  const { ollamaReachable = false, hasModels = false } = $props();

  // Smallest genuinely-capable chat model — keeps the first pull fast (~2 GB)
  // so a new user gets to a working chat quickly. Mirrors PullPage's pick.
  const STARTER_MODEL = 'llama3.2:3b';
  const SERVE_CMD = 'ollama serve';

  let copied = $state(false);

  async function copyServe() {
    try {
      await navigator.clipboard.writeText(SERVE_CMD);
      copied = true;
      setTimeout(() => (copied = false), 1500);
    } catch (_e) {
      /* clipboard blocked — the command is right there to copy by hand */
    }
  }

  function pullStarter() {
    setPendingPull(STARTER_MODEL);
    go('pull');
  }

  // Step 2 can't be acted on until Ollama is up — a pull needs the daemon.
  const modelStepLocked = $derived(!ollamaReachable && !hasModels);
</script>

<div class="bg-surface border border-border rounded-lg p-5 space-y-5">
  <div class="flex items-baseline gap-2">
    <h3 class="text-sm font-bold text-heading uppercase tracking-wider font-mono">Get started</h3>
    <span class="text-xs text-muted">two steps to your first chat</span>
  </div>

  <!-- Step ① — start Ollama -->
  <div class="flex gap-3">
    <span
      class="shrink-0 inline-flex items-center justify-center w-5 h-5 mt-0.5 rounded-full text-[11px] font-mono font-bold {ollamaReachable
        ? 'bg-success text-canvas'
        : 'bg-accent text-canvas'}"
      aria-hidden="true"
    >
      {ollamaReachable ? '✓' : '1'}
    </span>
    <div class="flex-1 min-w-0 space-y-2">
      <div class="text-sm {ollamaReachable ? 'text-muted' : 'text-heading font-medium'}">
        {ollamaReachable ? 'Ollama is running' : "Ollama isn't running"}
      </div>
      {#if !ollamaReachable}
        <div class="flex items-center gap-2">
          <code
            class="flex-1 min-w-0 font-mono text-xs bg-surface-2 text-body px-2 py-1.5 rounded border border-border truncate"
          >
            <span class="text-muted select-none">$&nbsp;</span>{SERVE_CMD}
          </code>
          <button
            onclick={copyServe}
            class="shrink-0 text-xs font-mono px-2 py-1.5 rounded bg-surface-2 border border-border text-muted hover:text-accent hover:border-accent transition-colors"
            aria-label="Copy the ollama serve command"
          >
            {copied ? '✓ copied' : 'copy'}
          </button>
        </div>
        <div class="flex items-center gap-1.5 text-xs font-mono text-muted">
          <span
            class="inline-block w-1.5 h-1.5 rounded-full bg-warning animate-pulse"
            aria-hidden="true"
          ></span>
          waiting for Ollama — this page connects on its own
        </div>
      {/if}
    </div>
  </div>

  <!-- Step ② — pull a model -->
  <div class="flex gap-3">
    <span
      class="shrink-0 inline-flex items-center justify-center w-5 h-5 mt-0.5 rounded-full text-[11px] font-mono font-bold {hasModels
        ? 'bg-success text-canvas'
        : modelStepLocked
          ? 'bg-surface-2 text-muted border border-border'
          : 'bg-accent text-canvas'}"
      aria-hidden="true"
    >
      {hasModels ? '✓' : '2'}
    </span>
    <div class="flex-1 min-w-0 space-y-2">
      <div
        class="text-sm {hasModels || modelStepLocked ? 'text-muted' : 'text-heading font-medium'}"
      >
        {hasModels ? 'A model is installed' : 'No models yet'}
      </div>
      {#if !hasModels}
        {#if modelStepLocked}
          <p class="text-xs text-muted">Start Ollama first, then add your first model here.</p>
        {:else}
          <p class="text-xs text-muted">
            Add a fast starter (~2 GB) — a good first model on modest hardware.
          </p>
          <div class="flex items-center gap-3">
            <Button variant="primary" size="sm" onclick={pullStarter}>
              Add {STARTER_MODEL}
            </Button>
            <button
              onclick={() => go('pull')}
              class="text-xs font-mono text-accent hover:underline"
            >
              browse all models →
            </button>
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>
