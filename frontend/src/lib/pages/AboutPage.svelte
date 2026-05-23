<script>
  import { Card, Code, Section } from '../components/ui/index.js';

  const tools = {
    frontend: [
      ['Svelte 5', 'reactive UI framework'],
      ['Vite', 'dev server + bundler'],
      ['Tailwind CSS 4', 'utility-first styling, @theme tokens'],
      ['ESLint + eslint-plugin-svelte', 'JS/Svelte linting'],
      ['Stylelint', 'CSS linting + token enforcement'],
      ['Prettier', 'consistent formatting'],
      ['svelte-check', 'JSDoc-driven type checking'],
      ['Vitest', 'unit + component tests'],
      ['Playwright', 'browser-based E2E smoke tests'],
      ['knip', 'dead-code + unused-dependency detection']
    ],
    backend: [
      ['FastAPI', 'async HTTP framework'],
      ['Uvicorn', 'ASGI server'],
      ['httpx', 'async HTTP client to Ollama'],
      ['Pydantic', 'request/response validation'],
      ['Ruff', 'linter + formatter'],
      ['mypy', 'strict type checking'],
      ['pytest + pytest-cov', 'tests + coverage gate'],
      ['pip-audit', 'dependency vulnerability scan']
    ],
    infra: [
      ['GitHub Actions', 'CI on every push and PR'],
      ['Husky', 'pre-commit hook'],
      ['Dependabot', 'automated dependency PRs'],
      ['validate-patterns.sh', 'design-system enforcement']
    ]
  };

  const principles = [
    {
      title: 'Single source of truth for color',
      detail:
        'Hex values live only in src/app.css. Components reference semantic tokens (bg-surface, text-heading) or var(--accent). The pattern validator fails the build if anything else slips in.'
    },
    {
      title: 'Sanctioned primitives',
      detail:
        'Buttons, cards, sections, tags, and stat rows have one canonical implementation in src/lib/components/ui/. Need a new variant? Add it there first; never paste-shape a one-off.'
    },
    {
      title: 'Tests gate merges',
      detail:
        'CI runs lint, type-check, unit tests, E2E, and a 70% coverage gate on the backend. Coverage drop, type error, or pattern violation fails the merge.'
    },
    {
      title: 'Tooling, not memory',
      detail:
        'Conventions are enforced by tools, not by remembering. Pre-commit catches drift locally; CI catches it on the way in.'
    }
  ];
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-4xl mx-auto space-y-8">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold text-heading mb-1">About</h1>
      <p class="text-sm text-muted">
        Octopus is a local Ollama model lab — chat with your models alongside live telemetry
        (tokens/sec, TTFT, GPU/VRAM, what's loaded). Built to fill the gap between Open WebUI
        (chat-only) and CLI tools (no UI).
      </p>
    </div>

    <!-- Octopus vs. Ollama -->
    <Card padding="lg">
      <Section title="octopus vs. ollama">
        <p class="text-sm text-body leading-relaxed mb-3">
          A fair question — Octopus can't do anything without Ollama. The short version:
          <strong class="text-heading"
            >Ollama is the engine; Octopus is the cockpit you run it from.</strong
          >
        </p>
        <div class="space-y-4">
          <div>
            <h3 class="text-sm font-semibold text-heading mb-0.5">Ollama — the engine</h3>
            <p class="text-sm text-muted leading-relaxed">
              The model runtime. It downloads model weights, loads them into memory, and does the
              actual inference. It runs headless — an API on <Code>127.0.0.1:11434</Code> plus a terminal
              CLI (<Code>ollama run</Code>, <Code>ollama pull</Code>). No window, no chat, no
              dashboard.
            </p>
          </div>
          <div>
            <h3 class="text-sm font-semibold text-heading mb-0.5">Octopus — the cockpit</h3>
            <p class="text-sm text-muted leading-relaxed">
              Runs no models of its own — it talks to Ollama's API. What it adds is everything
              around the model: a real chat window, live telemetry (tokens/sec, TTFT, VRAM, GPU), a
              Models page that says what each model is good for and whether it will run on your
              hardware, and a guided first run. Stop Ollama and Octopus has nothing to talk to —
              which is why it asks you to start it.
            </p>
          </div>
        </div>
        <p class="text-sm text-muted leading-relaxed mt-3">
          The same relationship a database GUI has with the database, or a car's dashboard with its
          engine: one does the work, the other makes it usable, visible, and safe.
        </p>
      </Section>
    </Card>

    <!-- Why -->
    <Card padding="lg">
      <Section title="why this exists">
        <p class="text-sm text-body leading-relaxed mb-2">
          Open WebUI and LM Studio cover chat. <Code>ollama ps</Code> and <Code>nvidia-smi</Code> cover
          stats. Promptfoo covers benchmarks. Nothing covers all three in one window.
        </p>
        <p class="text-sm text-body leading-relaxed">
          The eight tentacles fit: each "arm" runs a different model, the central UI coordinates the
          comparison.
        </p>
      </Section>
    </Card>

    <!-- Tech stack -->
    <Card padding="lg">
      <Section title="stack">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <div class="text-xs font-mono uppercase tracking-wide text-accent mb-2">Frontend</div>
            <dl class="space-y-1.5 text-sm">
              {#each tools.frontend as [name, desc] (name)}
                <div>
                  <dt class="font-mono text-heading text-xs">{name}</dt>
                  <dd class="text-muted text-xs">{desc}</dd>
                </div>
              {/each}
            </dl>
          </div>
          <div>
            <div class="text-xs font-mono uppercase tracking-wide text-accent mb-2">Backend</div>
            <dl class="space-y-1.5 text-sm">
              {#each tools.backend as [name, desc] (name)}
                <div>
                  <dt class="font-mono text-heading text-xs">{name}</dt>
                  <dd class="text-muted text-xs">{desc}</dd>
                </div>
              {/each}
            </dl>
          </div>
          <div>
            <div class="text-xs font-mono uppercase tracking-wide text-accent mb-2">Infra</div>
            <dl class="space-y-1.5 text-sm">
              {#each tools.infra as [name, desc] (name)}
                <div>
                  <dt class="font-mono text-heading text-xs">{name}</dt>
                  <dd class="text-muted text-xs">{desc}</dd>
                </div>
              {/each}
            </dl>
          </div>
        </div>
      </Section>
    </Card>

    <!-- Principles -->
    <Card padding="lg">
      <Section title="principles">
        <div class="space-y-4">
          {#each principles as p (p.title)}
            <div>
              <h3 class="text-sm font-semibold text-heading mb-0.5">{p.title}</h3>
              <p class="text-sm text-muted leading-relaxed">{p.detail}</p>
            </div>
          {/each}
        </div>
      </Section>
    </Card>

    <!-- Credits -->
    <Card padding="lg">
      <Section title="credits">
        <div class="text-sm text-body space-y-1.5">
          <p>
            Built by Seth Eheart, with <a
              class="text-accent hover:underline"
              href="https://claude.com/claude-code"
              target="_blank"
              rel="noopener noreferrer">Claude Code</a
            > on the keyboard.
          </p>
          <p class="text-muted text-xs">
            Design system inspired by raven (cream/ink-black light · phosphor-green dark). Icons
            from Lucide. Octocat is GitHub's mark.
          </p>
          <p class="text-muted text-xs">
            Source: <a
              class="text-accent hover:underline"
              href="https://github.com/seheart/octopus"
              target="_blank"
              rel="noopener noreferrer">github.com/seheart/octopus</a
            > · MIT licensed.
          </p>
        </div>
      </Section>
    </Card>
  </div>
</div>
