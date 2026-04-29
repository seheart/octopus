<script>
  /**
   * Roadmap — what's in flight, what's queued, what's parked.
   * Hand-curated. Edit this file as the project evolves.
   */
  import { Card } from '../components/ui/index.js';

  const now = [
    {
      title: 'Real benchmark integration (Promptfoo)',
      detail:
        'Wire Promptfoo into the backend so each model can be scored against a fixed prompt suite (HumanEval-style for code models, MMLU-lite for general). Results land on the model card with a freshness timestamp.',
      size: 'L'
    },
    {
      title: 'Arena mode',
      detail:
        'Side-by-side blind comparison: pick two models, send the same prompt, vote which response is better. Builds a personal Elo leaderboard from your taste — the killer feature for "which model do I actually use for X."',
      size: 'M'
    }
  ];

  const next = [
    {
      title: 'Conversation history persistence',
      detail:
        'Save chats to SQLite (alongside per-message stats). Sidebar list of past sessions so you can return to a thread. Currently chats vanish on refresh.',
      size: 'M'
    },
    {
      title: 'Static benchmark cards',
      detail:
        'Pull MMLU / HumanEval / GSM8K scores from Hugging Face Open LLM Leaderboard for each installed model. Shows up on the Models page so you can see "this is the right size class for your task."',
      size: 'S'
    },
    {
      title: 'Document RAG (drop a file in chat)',
      detail:
        'Use the already-installed nomic-embed-text to chunk + embed dropped documents. Inline citations point back to the source paragraph. The /api/chat backend already streams; just need the upload + embed pipeline.',
      size: 'M'
    },
    {
      title: 'Model warmup button',
      detail:
        'Models page → click any unloaded model to warm it into VRAM proactively. No-op chat request behind the scenes. Saves the 8-second cold-start TTFT on first real prompt.',
      size: 'XS'
    }
  ];

  const open = [
    {
      title: 'Bring back the favicon adaptive contrast',
      note: 'Current favicon uses prefers-color-scheme so it adapts to OS theme. But on tabs with mid-gray backgrounds (e.g. some terminal browsers) neither variant reads well. Consider a version with a subtle outline.'
    },
    {
      title: 'Should Octopus speak OpenAI-compatible API too?',
      note: 'Right now backend only proxies Ollama. Could trivially add OpenRouter / Anthropic / OpenAI endpoints — same telemetry instrumentation works for any streamed response. Question: does that dilute the "local lab" positioning?'
    },
    {
      title: 'Memory + tool use',
      note: 'Adding agent-style memory and tool calls turns octopus from a chat lab into something competitive with Open WebUI. But that scope creep undermines the "small, focused" pitch. Park unless there\'s a clear use case.'
    },
    {
      title: 'Multi-host: connect to remote Ollama',
      note: 'Backend hardcodes 127.0.0.1:11435 (overridable via OLLAMA_URL). Could become "saved connections" so you can flip between dev box, gaming rig, and a Mac mini. Tradeoff: settings sprawl.'
    }
  ];

  const recentlyShipped = [
    {
      label: 'Developer governance',
      detail:
        'ESLint · Stylelint · Prettier · svelte-check · Ruff · mypy · pytest-cov (95%) · GitHub Actions · husky · pattern validator banning arbitrary Tailwind hex colors in components. README + LICENSE.'
    },
    {
      label: 'Design system page',
      detail:
        'Live token gallery, primitives (Button, Card, Section, Tag, StatRow), governance rules. Flips with theme.'
    },
    {
      label: 'Header + footer + theme toggle',
      detail:
        'Multi-page nav (Chat / Models / System / Design / Settings), light/dark themes with localStorage persistence and OS preference detection.'
    },
    {
      label: 'SVG octopus logo + favicon',
      detail: '8-tentacle logo (asserted in tests), prefers-color-scheme favicon for browser tab.'
    },
    {
      label: 'GPU + tokens-per-second telemetry',
      detail:
        'FastAPI backend streams Ollama with TTFT and tokens/sec from eval_count/eval_duration. nvidia-smi parsed for VRAM bar.'
    },
    {
      label: 'GitHub repo + CI green',
      detail: 'Public/private repo synced; CI runs both stacks under a minute on push/PR.'
    }
  ];

  /** @param {string} size */
  function sizeBadgeClass(size) {
    switch (size) {
      case 'XS':
      case 'S':
        return 'bg-success/15 text-success';
      case 'M':
        return 'bg-accent/15 text-accent';
      case 'L':
      case 'XL':
        return 'bg-warning/15 text-warning';
      default:
        return 'bg-surface-2 text-muted';
    }
  }
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-4xl mx-auto space-y-10">
    <!-- Status bar -->
    <div
      class="flex items-center justify-between text-xs font-mono text-muted border-b border-border pb-2"
    >
      <div class="flex items-center gap-2">
        <span class="text-accent font-semibold">OCTOPUS.ROADMAP</span>
        <span aria-hidden="true">::</span>
        <span class="uppercase tracking-wide">Hand-curated · Edit RoadmapPage.svelte</span>
      </div>
      <div class="uppercase tracking-wide">
        {now.length} now · {next.length} next · {open.length} open
      </div>
    </div>

    <!-- Hero -->
    <div class="flex flex-col lg:flex-row gap-6">
      <div class="flex-1 min-w-0">
        <h1 class="text-2xl font-bold text-heading mb-1">Roadmap</h1>
        <p class="text-sm text-muted">
          What's in flight, what's queued, and what's parked. Sized in t-shirts (XS / S / M / L /
          XL). Open questions are bigger calls that need a design pass before they become work.
        </p>
      </div>
      <aside class="lg:w-72 lg:flex-shrink-0">
        <Card>
          <div class="text-xs font-mono uppercase tracking-wide text-muted mb-3">Size legend</div>
          <dl class="space-y-1.5 text-sm font-mono">
            {#each [{ k: 'XS', v: 'typo · copy tweak' }, { k: 'S', v: '~1 day refactor' }, { k: 'M', v: '2–3 day feature' }, { k: 'L', v: 'week-long initiative' }, { k: 'XL', v: '2+ weeks · multi-phase' }] as row (row.k)}
              <div class="flex items-baseline gap-3">
                <dt class="text-accent w-7 flex-shrink-0">{row.k}</dt>
                <dd class="text-muted">{row.v}</dd>
              </div>
            {/each}
          </dl>
        </Card>
      </aside>
    </div>

    <!-- 01 // Now -->
    <section>
      <div
        class="text-xs font-mono text-muted uppercase tracking-widest mb-3 flex items-center gap-3"
      >
        <span>01 // Now</span>
        <span class="flex-1 border-t border-dashed border-border"></span>
        <span class="text-accent normal-case">In flight</span>
      </div>
      <div class="space-y-3">
        {#each now as item (item.title)}
          <Card>
            <div class="flex items-baseline justify-between gap-3 mb-2">
              <h3 class="text-base font-semibold text-heading">{item.title}</h3>
              <span
                class="inline-block text-xs font-mono font-bold px-2 py-0.5 rounded {sizeBadgeClass(
                  item.size
                )}">{item.size}</span
              >
            </div>
            <p class="text-sm text-body leading-relaxed">{item.detail}</p>
          </Card>
        {/each}
      </div>
    </section>

    <!-- 02 // Next -->
    <section>
      <div
        class="text-xs font-mono text-muted uppercase tracking-widest mb-3 flex items-center gap-3"
      >
        <span>02 // Next</span>
        <span class="flex-1 border-t border-dashed border-border"></span>
        <span class="text-warning normal-case">Queued</span>
      </div>
      <div class="space-y-3">
        {#each next as item, i (item.title)}
          <Card>
            <div class="flex items-baseline justify-between gap-3 mb-2">
              <h3 class="text-base font-semibold text-heading">
                <span class="text-muted font-mono mr-2">{String(i + 1).padStart(2, '0')}</span>
                {item.title}
              </h3>
              <span
                class="inline-block text-xs font-mono font-bold px-2 py-0.5 rounded {sizeBadgeClass(
                  item.size
                )}">{item.size}</span
              >
            </div>
            <p class="text-sm text-body leading-relaxed">{item.detail}</p>
          </Card>
        {/each}
      </div>
    </section>

    <!-- 03 // Open questions -->
    <section>
      <div
        class="text-xs font-mono text-muted uppercase tracking-widest mb-3 flex items-center gap-3"
      >
        <span>03 // Open Questions</span>
        <span class="flex-1 border-t border-dashed border-border"></span>
        <span class="text-muted normal-case">Needs design</span>
      </div>
      <div class="space-y-3">
        {#each open as item (item.title)}
          <Card>
            <h3 class="text-sm font-semibold text-heading mb-1">{item.title}</h3>
            <p class="text-sm text-muted leading-relaxed">{item.note}</p>
          </Card>
        {/each}
      </div>
    </section>

    <!-- 04 // Recently shipped -->
    <section>
      <div
        class="text-xs font-mono text-muted uppercase tracking-widest mb-3 flex items-center gap-3"
      >
        <span>04 // Recently Shipped</span>
        <span class="flex-1 border-t border-dashed border-border"></span>
        <span class="text-success normal-case">Done</span>
      </div>
      <div class="space-y-2">
        {#each recentlyShipped as r (r.label)}
          <div class="flex items-baseline gap-3 border-l-2 border-success pl-3 py-1">
            <span class="text-sm font-medium text-heading shrink-0">{r.label}</span>
            <span class="text-xs text-muted">— {r.detail}</span>
          </div>
        {/each}
      </div>
    </section>
  </div>
</div>
