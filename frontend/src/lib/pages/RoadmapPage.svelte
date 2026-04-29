<script>
  /**
   * Roadmap — what's in flight, what's queued, what's parked.
   * Hand-curated. Edit this file as the project evolves.
   */
  import { Card } from '../components/ui/index.js';

  const now = [
    {
      title: 'Frictionless install — "open it and get it" in 60 seconds',
      detail:
        'A non-developer (or a frustrated developer) should be able to go from zero to chatting with a local model in under a minute. One-line install from GitHub (curl|bash or a single docker compose up). Auto-detect Ollama, including the awkward "default port is taken" case. One-command start (./start.sh exists; needs to also seed sensible defaults if Ollama is bare). A landing page that explains what just got installed and what to do first — no scavenger hunt through README. The README itself leads with "60 seconds to first chat", not architecture. This is also a permanent design constraint: every feature added later must preserve the "open it and get it" property. The whole reason Open WebUI failed me was that I — a person who builds software for a living — could not figure it out without a half-hour of fiddling. Octopus must never feel that way. Eight arms, calm and approachable; not enterprise software with a dashboard glued on.',
      size: 'L'
    },
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
        'Models page → click any unloaded model to warm it into VRAM proactively. No-op chat request behind the scenes. Cold-start hint is in place; missing the explicit button.',
      size: 'XS'
    },
    {
      title: 'Regenerate / edit / branch on chat messages',
      detail:
        'Standard chat affordances. Regenerate is the cheapest win (rerun last assistant message); edit + branch are bigger lifts that touch persistence.',
      size: 'S'
    }
  ];

  const open = [
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
      label: 'UX overhaul',
      detail:
        'Markdown rendering for assistant responses (marked + DOMPurify, XSS-tested). Stop button + AbortController. Copy-message hover affordance. Auto-focus chat input on load. 4 clickable example prompts on empty state. Cold-start "warming up…" hint after 2.5s of silence. Errors render inline instead of being silently swallowed.'
    },
    {
      label: 'Connection banner',
      detail:
        'Top-of-page red alert when backend is unreachable. Connection store tracks state across pages; needs 2 consecutive failures to flip "down" so we do not flash on a single hiccup.'
    },
    {
      label: 'Models page click → set chat model',
      detail:
        'New selectedModel store backed by localStorage. Models page cards now actually wire up to chat (was a TODO). Default model also editable from Settings.'
    },
    {
      label: 'System page redo',
      detail:
        'Ollama connection card (status, version, url) · Inventory summary (count, total params, disk, VRAM) · Host card (CPU, cores, uptime, memory bar, disk bar) · GPU panel · Loaded-in-VRAM list with live tag. Backend gained /api/ollama and /api/host endpoints (no psutil — pure stdlib parsing /proc).'
    },
    {
      label: 'About page',
      detail:
        'Why this exists, full tech-stack table (frontend / backend / infra), governance principles, credits + license. Lives in the footer between Roadmap and the GitHub icon.'
    },
    {
      label: 'Tier 2 governance — actually rock solid now',
      detail:
        'Playwright E2E (8 smoke tests, mocked /api so no Ollama needed) · knip dead-code detection · pip-audit + npm audit (caught 2 CVEs on the first run) · Dependabot weekly · branch protection on main. CI now has 3 jobs (Frontend / Backend / E2E) all required.'
    },
    {
      label: 'Tier 1 governance + design system',
      detail:
        'ESLint · Stylelint · Prettier · svelte-check · Ruff · mypy · pytest-cov (90%) · husky pre-commit · pattern validator banning arbitrary Tailwind hex in components. Sanctioned UI primitives (Button, Card, Code, Section, Tag, StatRow). Living Design page in both themes.'
    },
    {
      label: 'Multi-page layout + theme system',
      detail:
        'Header (Chat / Models / Settings) + footer (System / Design / Roadmap / About / GitHub / theme). Light (cream/ink-black) and dark (black/phosphor-green) with localStorage persistence and OS preference detection. SVG octopus logo (8 tentacles, asserted in tests) + adaptive favicon.'
    },
    {
      label: 'GPU + tokens-per-second telemetry',
      detail:
        'FastAPI backend streams Ollama with TTFT and tokens/sec from eval_count/eval_duration. nvidia-smi parsed for VRAM bar in chat sidebar and System page.'
    },
    {
      label: 'GitHub repo + CI green',
      detail: 'Repo synced to seheart/octopus; CI runs all 3 jobs under 90s on every push/PR.'
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
